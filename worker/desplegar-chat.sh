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

# ── Qué kits de marca tiene ESTA copia ───────────────────────────────────
#
# Se imprime antes de compilar nada, y no es decoración: el 3/9/2026 un
# despliegue salió «bien» de punta a punta con el motor nuevo y los kits
# viejos. La causa fue un asterisco —`cp -r /tmp/nuevo/worker/*` no copia
# `.claude`, porque el shell saltea los nombres que empiezan con punto— y no
# dejó ningún rastro: nueve carpetas copiadas, código de salida cero.
#
# Lo que sí se puede ver de un vistazo es la fecha de cada kit. Si acabás de
# traer código nuevo y acá aparece la fecha de la semana pasada, la copia no
# incluyó las marcas: pará y copiá con `cp -r /tmp/nuevo/worker/. .` — el punto
# en vez del asterisco. Ver DESPLEGAR.md, paso 1.
echo "▸ 0/4  Kits de marca en esta copia"
for KIT in .claude/skills/*/; do
  [ -f "${KIT}marca.json" ] || continue
  NOMBRE="$(basename "$KIT")"
  # Las que empiezan con guión bajo son borradores y el motor no las ve.
  CUANTAS="$(find "${KIT}plantillas" -mindepth 1 -maxdepth 1 -type d \
             -not -name '_*' 2>/dev/null | wc -l)"
  FECHA="$(date -r "${KIT}marca.json" '+%d/%m %H:%M' 2>/dev/null || echo '?')"
  echo "  · ${NOMBRE}: ${CUANTAS} plantillas · marca.json del ${FECHA}"
done

# ── De dónde sale la lista de clientes ───────────────────────────────────
#
# Dos caminos, y el script elige solo:
#
#   · Si existe el secreto `clientes-registro`, ÉSE manda. El worker lo lee en
#     cada corrida, así que sumar un cliente es `python3 herramientas/registro.py
#     agregar` y nada más: este script no hace falta para eso. Acá sólo se
#     monta el secreto y se pregunta qué marcas hay, para decidir si pedir la
#     clave de Magnific. Ver `app/registro.py`.
#   · Si no existe, es el camino anterior: `clientes.json` más un secreto por
#     cliente. Sigue andando igual. Para pasar al registro una sola vez:
#     `python3 herramientas/registro.py crear`.
if gcloud secrets describe clientes-registro --quiet >/dev/null 2>&1; then
  REGISTRO=1
  CLIENTES_JSON=""
  SECRETOS_RUN="CLIENTES_REGISTRO=clientes-registro:latest,"
  MARCAS=$(python3 herramientas/registro.py marcas)
  FALTANTES=""
  echo "▸ Clientes: del registro «clientes-registro» → ${MARCAS}"
else
  REGISTRO=""
  CLIENTES_JSON=$(python3 clientes.py json)
  SECRETOS_RUN=$(python3 clientes.py run-secrets)
  MARCAS=$(python3 clientes.py marcas)
  FALTANTES=$(python3 clientes.py faltantes)
fi

if [ -z "$MARCAS" ]; then
  echo "✗ Ningún cliente con URL cargada en clientes.json"
  exit 1
fi
if [ -n "$FALTANTES" ]; then
  echo "⚠ Sin URL, no se van a atender: ${FALTANTES}"
fi

if [ -z "$REGISTRO" ]; then
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
fi

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

if [ -z "$REGISTRO" ]; then
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
else
  echo "▸ 1/4  Secretos por cliente: no hacen falta, están en el registro"
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
FAL_SECRETO=""
GEMINI_SECRETO=""
if [ -n "$REGISTRO" ]; then
  SOLICITAN_REELS=$(for M in $MARCAS; do
    python3 -c "import json,sys; d=json.load(open('.claude/skills/$M/marca.json')); print('$M') if d.get('reels') else None" 2>/dev/null; done | tr '\n' ' ')
else
  SOLICITAN_REELS=$(python3 clientes.py reels 2>/dev/null || true)
fi
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

  # ── El segundo proveedor de video: fal.ai ───────────────────────────────
  #
  # Igual de opcional que Magnific y por el mismo motivo: sin la clave, los
  # pedidos que pidan fal se quedan quietos en `pendiente` sin gastar nada, y
  # los de Magnific siguen saliendo. El worker mira la clave del proveedor de
  # CADA fila, no una sola.
  #
  # La clave se pega acá, en la terminal, y va derecho a Secret Manager. Nunca
  # al código, nunca a un chat.
  if ! gcloud secrets describe fal-api-key --quiet >/dev/null 2>&1; then
    echo "  fal.ai es el otro proveedor de video (MiniMax H3 Max). Es opcional:"
    echo "  dejá vacío y Enter si todavía no lo vas a usar."
    read -rs -p "  Pegá la API key de fal.ai y Enter (no se ve): " K; echo
    if [ -n "$K" ]; then
      printf '%s' "$K" | gcloud secrets create fal-api-key --data-file=- --quiet
    else
      echo "  · sin fal: los reels siguen saliendo por Magnific"
    fi
    unset K
  fi
  if gcloud secrets describe fal-api-key --quiet >/dev/null 2>&1; then
    gcloud secrets add-iam-policy-binding fal-api-key \
      --member="serviceAccount:${SA}" \
      --role="roles/secretmanager.secretAccessor" --quiet >/dev/null
    FAL_SECRETO="FAL_CLAVE=fal-api-key:latest,"
    echo "  · fal-api-key listo → FAL_CLAVE"
  fi
fi

# ── La clave de Gemini: elegir los tramos de un video largo ──────────────
#
# Opcional como las otras. Sin ella, `montar_reel` sigue cortando por audio,
# como hasta el 2/9/2026. Con ella, cuando el pedido trae una instrucción y
# el material es más largo que el reel, Gemini agéntico mira el video y dice
# qué tramos entran (ver motor/mirar.py). La clave es la de Google AI Studio;
# va a Secret Manager, nunca al código ni a un chat.
if [ -n "$SOLICITAN_REELS" ]; then
  if ! gcloud secrets describe gemini-api-key --quiet >/dev/null 2>&1; then
    echo "▸ 1e/4  La clave de Gemini (elegir tramos de un video largo). Opcional:"
    echo "  dejá vacío y Enter si todavía no la vas a usar."
    read -rs -p "  Pegá la API key de Gemini y Enter (no se ve): " K; echo
    if [ -n "$K" ]; then
      printf '%s' "$K" | gcloud secrets create gemini-api-key --data-file=- --quiet
    else
      echo "  · sin Gemini: montar_reel corta por audio, como hasta ahora"
    fi
    unset K
  fi
  if gcloud secrets describe gemini-api-key --quiet >/dev/null 2>&1; then
    gcloud secrets add-iam-policy-binding gemini-api-key \
      --member="serviceAccount:${SA}" \
      --role="roles/secretmanager.secretAccessor" --quiet >/dev/null
    GEMINI_SECRETO="GEMINI_CLAVE=gemini-api-key:latest,"
    echo "  · gemini-api-key listo → GEMINI_CLAVE"
  fi
fi

# ── Antes de gastar cinco minutos de build ────────────────────────────────
#
# El 1/9/2026 un despliegue murió con «dockerfile parse error line 1: unknown
# instruction: ≈≈». La primera línea del Dockerfile decía `≈≈`: dos caracteres
# que se escribieron sin querer adentro de nano —en un Mac `Option+X` produce
# `≈`— buscando el `Ctrl+X` que lo cierra.
#
# Cloud Build lo detectó igual, pero recién después de subir el contexto y
# arrancar Docker, y con un mensaje que no dice de dónde salió. Preguntarlo
# acá cuesta un segundo.
if [[ -f Dockerfile ]]; then
  primera="$(grep -vE '^\s*(#|$)' Dockerfile | head -1)"
  if [[ ! "$primera" =~ ^([Aa][Rr][Gg]|[Ff][Rr][Oo][Mm])[[:space:]] ]]; then
    echo "✗ El Dockerfile no arranca con FROM. La primera línea con algo dice:"
    echo "    $primera"
    echo
    echo "  Docker no va a poder leerlo. Casi siempre es basura que quedó de"
    echo "  editarlo a mano. Se saca con:"
    echo "    python3 herramientas/limpiar-dockerfile.py $(pwd)/Dockerfile"
    exit 1
  fi
fi

# ── Las pruebas que cuidan la plata del cliente ───────────────────────────
#
# Son tres y las tres corren en segundos, sin red y sin gastar nada. Están acá
# —antes del build— porque las tres vigilan cosas que sólo se descubren cuando
# ya se cobró: un precio que se dice mal, un pedido que devuelve otra cosa de
# la que se pidió, y una pieza que sale rota y se marca «listo».
#
# La del revisor necesita ffmpeg para fabricar sus casos. Si no está, se
# saltea con un aviso en vez de frenar el despliegue: no tener ffmpeg acá no
# dice nada sobre el código, y frenar por eso enseña a saltear las pruebas.
PRUEBAS="probar-precios.py probar-video-solo.py"
if command -v ffmpeg >/dev/null 2>&1; then
  PRUEBAS="$PRUEBAS probar-revisor.py"
else
  echo "  · sin ffmpeg acá: no corro probar-revisor.py"
fi
for PRUEBA in $PRUEBAS; do
  if ! SALIDA="$(python3 "herramientas/$PRUEBA" 2>&1)"; then
    echo "✗ Falló herramientas/$PRUEBA — no despliego:"
    echo "$SALIDA" | sed 's/^/    /'
    exit 1
  fi
done
echo "  · precios, separación video/pieza y revisor: en orden"

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
# Para volver al modelo anterior:  WHISPER_MODELO=medium ./desplegar-chat.sh
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
  --set-env-vars "^|^${CLIENTES_JSON:+CLIENTES=${CLIENTES_JSON}|}BUCKET=disenos|SA_EMAIL=${SA}|MAX_POR_CICLO=5|MARGEN=${MARGEN:-2.0}|WHISPER_MODELO=${WHISPER_MODELO:-large-v3}" \
  --set-secrets "ANTHROPIC_API_KEY=anthropic-key:latest,${MAGNIFIC_SECRETO}${FAL_SECRETO}${GEMINI_SECRETO}${ASISTIME_SECRETO}${SECRETOS_RUN}" \
  --quiet

echo "▸ 3/4  Reloj: una corrida por minuto (el webhook está bloqueado por política de la org)"
URL="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROYECTO}/jobs/${JOB}:run"
gcloud scheduler jobs delete "${JOB}-red-seguridad" --location "$REGION" --quiet 2>/dev/null || true
gcloud scheduler jobs create http "${JOB}-red-seguridad" \
  --location "$REGION" --schedule "* * * * *" --time-zone "America/Montevideo" \
  --uri "$URL" --http-method POST \
  --oauth-service-account-email "$SA" --quiet

# ── El catálogo que lee el agente ────────────────────────────────────────
#
# El catálogo de plantillas es un documento en Asistime que el agente consulta
# antes de decidir qué hacer, y **manda sobre su propio prompt**: si el
# documento dice una cosa y el prompt otra, el agente le cree al documento.
#
# Lo genera `motor/plantillas.catalogo` desde los contratos de las plantillas,
# pero republicarlo era un comando aparte que había que acordarse de correr, y
# nadie lo corrió. El 1/9/2026 el de Boss llevaba una semana viejo diciendo que
# **el video necesitaba código**; alguien pidió un video, el agente leyó eso,
# contestó que no se podía y anotó un pedido de cambio de motor. Una hora antes
# el sistema había hecho exactamente ese video.
#
# Un documento que se declara «generado por el motor» y que en realidad hay que
# acordarse de subir a mano no está generado por el motor: es un archivo suelto
# que envejece mintiendo. Por eso ahora se republica acá, en cada despliegue,
# que es lo que su propia descripción decía que pasaba.
#
# Si falla, el despliegue NO se cae: el catálogo anterior sigue sirviendo y lo
# que se pierde es que esté al día. Se avisa y se sigue.
echo "▸ 3b/4  Catálogo de plantillas al día en Asistime"
# Con registro, la lista sale del REGISTRO y no de `clientes.json`.
#
# Miraban listas distintas: el worker atendía cuatro clientes y esto veía tres,
# porque Asistime estaba en el registro y nunca se agregó al json. El catálogo
# de Asistime se quedó viejo el 2/9/2026 sin que nada fallara — y un catálogo
# viejo no avisa: el agente sigue leyendo campos que ya no existen.
#
# La clave la busca el propio `publicar-catalogo.py` en el registro cuando no
# viene por variable de entorno, igual que hace el worker.
if [ -n "$REGISTRO" ]; then
  for MARCA in $MARCAS; do
    if SALIDA="$(python3 herramientas/publicar-catalogo.py "$MARCA" 2>&1)"; then
      echo "  · $MARCA: ${SALIDA##*· }"
    else
      echo "  ⚠ $MARCA: no pude republicar el catálogo (sigue el anterior):"
      printf '%s\n' "$SALIDA" | tail -3 | sed 's/^/      /'
    fi
    # El prompt sólo para las marcas que lo generan del repo; el script se
    # niega solo en las demás, así que su negativa no es un error acá.
    if SALIDA="$(python3 herramientas/publicar-prompt.py "$MARCA" 2>&1)"; then
      echo "  · $MARCA: ${SALIDA##*· }"
    fi
  done
else
while read -r MARCA VARIABLE SECRETO <&3; do
  if [ -z "${MARCA:-}" ]; then continue; fi
  if ! CLAVE="$(gcloud secrets versions access latest --secret="$SECRETO" 2>/dev/null)"; then
    echo "  ⚠ $MARCA: sin clave de Asistime, su catálogo queda como estaba"
    continue
  fi
  if SALIDA="$(env "$VARIABLE=$CLAVE" python3 herramientas/publicar-catalogo.py "$MARCA" 2>&1)"; then
    echo "  · $MARCA: catálogo republicado"
  else
    echo "  ⚠ $MARCA: no pude republicar el catálogo (sigue el anterior):"
    printf '%s\n' "$SALIDA" | tail -3 | sed 's/^/      /'
  fi
  unset CLAVE
done 3< <(python3 clientes.py asistime)
fi

echo "▸ 4/4  Listo — clientes: ${MARCAS}"
echo
echo "Probalo insertando una fila en 'disenos' desde alguna app, o a mano:"
echo "  gcloud run jobs execute ${JOB} --region ${REGION} --wait"
