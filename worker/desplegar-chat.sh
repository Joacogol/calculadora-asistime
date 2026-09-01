#!/usr/bin/env bash
# Despliega el worker. Un solo motor que atiende a todos los clientes de
# `clientes.json`, cada uno con su propio Supabase.
set -euo pipefail

PROYECTO="boss-padel-disenos"
REGION="southamerica-east1"
SA="worker-boss-padel@${PROYECTO}.iam.gserviceaccount.com"
JOB="boss-chat"

# Lo PRIMERO es comprobar que hay sesión. Sin esto el script llegaba a pedir la
# service_role key por teclado y recién después moría con «You do not currently
# have an active account selected»: la clave se tipeaba para nada, y Cloud Shell
# cierra la sesión cada tanto así que pasa seguido.
if ! gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | grep -q .; then
  echo "✗ No hay ninguna cuenta activa en gcloud."
  echo "  Corré:  gcloud auth login"
  exit 1
fi
if [ "$(gcloud config get-value project 2>/dev/null)" != "$PROYECTO" ]; then
  echo "⚠ El proyecto actual no es ${PROYECTO}. Lo cambio."
  gcloud config set project "$PROYECTO" --quiet
fi

CLIENTES_JSON=$(python3 clientes.py json)
SECRETOS_RUN=$(python3 clientes.py run-secrets)
MARCAS=$(python3 clientes.py marcas)
FALTANTES=$(python3 clientes.py faltantes)

if [ -z "$MARCAS" ]; then
  echo "✗ Ningún cliente con URL cargada en clientes.json"
  exit 1
fi
if [ -n "$FALTANTES" ]; then
  echo "⚠ Sin URL, no se van a atender: ${FALTANTES}"
fi

echo "▸ 1/4  Un secreto por cliente (la service_role key de cada Supabase)"
# La clave no está ni en este script ni en clientes.json: se pide por teclado
# la primera vez y queda en Secret Manager. `read -rs` no la muestra en
# pantalla ni la deja en el historial del shell.
for S in $(python3 clientes.py secretos); do
  if ! gcloud secrets describe "$S" --quiet >/dev/null 2>&1; then
    read -rs -p "  Pegá la service_role key para «$S» y Enter (no se ve): " K; echo
    if [ -z "$K" ]; then echo "  ✗ vacía — cancelo"; exit 1; fi
    printf '%s' "$K" | gcloud secrets create "$S" --data-file=- --quiet
    unset K
  fi
  gcloud secrets add-iam-policy-binding "$S" \
    --member="serviceAccount:${SA}" \
    --role="roles/secretmanager.secretAccessor" --quiet >/dev/null
  echo "  · $S listo"
done

# ── Las claves de la API de Asistime ──────────────────────────────────────
# Con ellas el worker lee el manual de marca que edita cada cliente. Se piden
# igual que las de Supabase: por teclado, sin eco, y quedan en Secret Manager.
#
# Hay UNA POR CLIENTE, no una sola. La clave de Asistime está atada a un
# tenant: la de un cliente contra los documentos de otro contesta 403. Cada
# marca declara la suya en su `marca.json` (`asistime.clave_env` y
# `clave_secreto`), que es donde `app/manual.py` ya buscaba el nombre.
#
# Esto estaba escrito a mano con el secreto de Boss, y el efecto era peor que
# un error: cada despliegue borraba del job la variable del segundo cliente, y
# ese cliente pasaba a diseñar SIN su manual de marca. Sin fallar y sin avisar,
# hasta que salía una pieza con un precio viejo.
#
# El permiso de lectura para la cuenta de servicio va SIEMPRE, no sólo cuando
# el secreto se crea. Sin esa línea el despliegue sale bien y el job falla
# después, al arrancar, con un error de permisos: el peor momento para
# enterarse y el más difícil de atar a este archivo.
ASISTIME_SECRETO=""

echo "▸ 1b/4  Una clave de Asistime por cliente (para leer su manual de marca)"
# La lista entra por el descriptor 3 y no por la entrada estándar: si entrara
# por la estándar, el `read` que pide la clave se comería la línea del cliente
# siguiente en vez de esperar el teclado.
while read -r MARCA VARIABLE SECRETO <&3; do
  if [ -z "${MARCA:-}" ]; then continue; fi
  if ! gcloud secrets describe "$SECRETO" --quiet >/dev/null 2>&1; then
    echo "  «$MARCA» todavía no tiene su clave de Asistime."
    echo "  Si no la tenés a mano, dejá vacío y Enter: se despliega igual y sus"
    echo "  piezas salen con el manual del skill, como antes de esto."
    read -rs -p "  Pegá la clave (X-API-KEY) de «$MARCA» y Enter (no se ve): " K; echo
    if [ -z "$K" ]; then
      echo "  ⚠ sin clave: «$MARCA» va a diseñar SIN su manual de marca"
      continue
    fi
    printf '%s' "$K" | gcloud secrets create "$SECRETO" --data-file=- --quiet
    unset K
  fi
  gcloud secrets add-iam-policy-binding "$SECRETO" \
    --member="serviceAccount:${SA}" \
    --role="roles/secretmanager.secretAccessor" --quiet >/dev/null
  ASISTIME_SECRETO="${ASISTIME_SECRETO}${VARIABLE}=${SECRETO}:latest,"
  echo "  · $SECRETO listo → $VARIABLE"
done 3< <(python3 clientes.py asistime)

# Una marca que declara su clave y no la tiene cargada es exactamente el caso
# que hacía falta que se viera. Se dice acá, junta y al final, porque en el
# medio del despliegue se pierde entre líneas de gcloud.
SIN_CLAVE=""
while read -r MARCA VARIABLE _; do
  if [ -z "${MARCA:-}" ]; then continue; fi
  case ",$ASISTIME_SECRETO" in *",$VARIABLE="*) ;; *) SIN_CLAVE="$SIN_CLAVE $MARCA" ;; esac
done < <(python3 clientes.py asistime)
if [ -n "$SIN_CLAVE" ]; then
  echo "  ⚠ SIN manual de marca:$SIN_CLAVE — sus piezas ignoran lo que el"
  echo "    cliente escribió (precios, qué foto usar, el tono)."
fi

# ── La clave de Magnific, para los reels ──────────────────────────────────
# Es UNA sola para todo el worker, y no una por cliente: la cuenta de Magnific
# es nuestra y los créditos salen del mismo balde. Lo que separa a un cliente
# de otro es el tope de `marca.json` (`reels.creditos_maximos_mes`), no la
# clave.
#
# NO es la del conector de Magnific: ese entra con OAuth de una persona y sirve
# sólo adentro de un chat. El worker corre solo y necesita llave propia.
#
# Es opcional a propósito. Sin ella el despliegue sale igual y los pedidos de
# reel se quedan quietos en `pendiente` —el worker mira la clave ANTES de tocar
# la fila—, así que no se pierde ningún pedido ni se gasta nada, y salen solos
# en la primera corrida después de cargarla.
MAGNIFIC_SECRETO=""
SOLICITAN_REELS=$(python3 clientes.py reels 2>/dev/null || true)
if [ -n "$SOLICITAN_REELS" ]; then
  echo "▸ 1c/4  La clave de Magnific (reels de video) — la piden: ${SOLICITAN_REELS}"
  if ! gcloud secrets describe magnific-api-key --quiet >/dev/null 2>&1; then
    echo "  Si no la tenés a mano, dejá vacío y Enter: se despliega igual y los"
    echo "  pedidos de reel esperan en la cola sin gastar créditos."
    read -rs -p "  Pegá la API key de Magnific y Enter (no se ve): " K; echo
    if [ -n "$K" ]; then
      printf '%s' "$K" | gcloud secrets create magnific-api-key --data-file=- --quiet
    else
      echo "  ⚠ sin clave: los reels van a quedar esperando en «pendiente»"
    fi
    unset K
  fi
  if gcloud secrets describe magnific-api-key --quiet >/dev/null 2>&1; then
    gcloud secrets add-iam-policy-binding magnific-api-key \
      --member="serviceAccount:${SA}" \
      --role="roles/secretmanager.secretAccessor" --quiet >/dev/null
    MAGNIFIC_SECRETO="MAGNIFIC_CLAVE=magnific-api-key:latest,"
    echo "  · magnific-api-key listo → MAGNIFIC_CLAVE"
  fi
fi

echo "▸ 2/4  Desplegando el job (compila la imagen, tarda unos minutos)"
# ── Por qué 8 núcleos y no 2 ──────────────────────────────────────────────
# Montar un reel es, casi todo, codificar video: es trabajo de CPU puro y se
# reparte bien entre núcleos. Y Cloud Run cobra por NÚCLEO-SEGUNDO, no por
# corrida: cuatro veces la máquina durante un tercio del tiempo sale
# aproximadamente lo mismo por reel. La cuenta no da exactamente igual —x264
# no escala perfecto y el reparto se pierde un poco— pero la diferencia de
# precio es de centavos, y la de espera es de minutos.
#
# Con 2 núcleos, el primer reel que pidió un cliente de verdad se comió los 30
# minutos de límite y murió sin terminar. Un cliente no espera media hora por
# un reel: si esto tarda, no se vende.
#
# La memoria sube a 4 GiB por dos motivos. Uno, Cloud Run pide un mínimo de
# memoria para dar 8 núcleos. Dos, en el peor momento conviven el modelo de
# transcripción (~1 GB), un Chromium y un ffmpeg trabajando sobre cuadros de
# 1080×1920: con 2 GiB eso estaba al filo, y quedarse sin memoria mata el
# proceso igual que el reloj, y con menos rastro todavía.
# El separador ^|^ es porque CLIENTES es un JSON con comas adentro y gcloud
# usa la coma para separar variables: sin esto, parte el JSON al medio.
#
# `WHISPER_MODELO` va acá EXPLÍCITO, y no confiado al valor por defecto del
# código, por una razón que costó un susto: `--set-env-vars` **reemplaza la
# lista entera**. Un `gcloud run jobs update --update-env-vars` hecho a mano
# —por ejemplo para probar otro modelo— sobrevive hasta el próximo despliegue
# y después desaparece sin que nadie lo note. Con la variable acá, lo que
# manda es este archivo y se ve de un vistazo.
#
# Para volver al modelo chico:  WHISPER_MODELO=small ./desplegar-chat.sh
#
# La memoria pasó de 4 a 8 GiB junto con `medium`, y no es por las dudas:
# medido, `medium` tiene un pico de 2,1 GiB contra los 781 MiB de `small`, y
# si el modelo no está horneado en la imagen se le suman los 1,5 GiB que
# ocupa bajarlo —en Cloud Run el disco del contenedor es memoria—. Con 4 GiB
# eso no entraba y el reel no terminaba nunca. Ver `DESPLEGAR.md`.
gcloud run jobs deploy "$JOB" \
  --source . \
  --region "$REGION" \
  --service-account "$SA" \
  --memory 8Gi --cpu 8 --task-timeout 30m --max-retries 1 \
  --command python --args="-m,app.chat" \
  --set-env-vars "^|^CLIENTES=${CLIENTES_JSON}|BUCKET=disenos|SA_EMAIL=${SA}|MAX_POR_CICLO=5|MARGEN=${MARGEN:-2.0}|WHISPER_MODELO=${WHISPER_MODELO:-medium}" \
  --set-secrets "ANTHROPIC_API_KEY=anthropic-key:latest,${MAGNIFIC_SECRETO}${ASISTIME_SECRETO}${SECRETOS_RUN}" \
  --quiet

echo "▸ 3/4  Reloj: una corrida por minuto (el webhook está bloqueado por política de la org)"
URL="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROYECTO}/jobs/${JOB}:run"
gcloud scheduler jobs delete "${JOB}-red-seguridad" --location "$REGION" --quiet 2>/dev/null || true
gcloud scheduler jobs create http "${JOB}-red-seguridad" \
  --location "$REGION" --schedule "* * * * *" --time-zone "America/Montevideo" \
  --uri "$URL" --http-method POST \
  --oauth-service-account-email "$SA" --quiet

echo "▸ 4/4  Listo — clientes: ${MARCAS}"
echo
echo "Probalo insertando una fila en 'disenos' desde alguna app, o a mano:"
echo "  gcloud run jobs execute ${JOB} --region ${REGION} --wait"
