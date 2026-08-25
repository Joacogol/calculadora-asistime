# Desplegar el worker

Para quien va a correr los comandos. Si no sos vos, pasale esta página entera.

Hace falta: acceso a `gcloud` en el proyecto **boss-padel-disenos**, y acceso al
SQL Editor del Supabase de Boss. Nada más.

Todo esto ya corrió antes: el worker está desplegado desde agosto y esto es una
actualización, no una instalación. Los pasos 3 y 4 son los únicos que no se
hicieron nunca.

---

## Antes de empezar: qué es esto y por qué importa

El worker es un **Cloud Run job**: arranca, vacía la cola de pedidos, y
termina. Un reloj lo enciende **una vez por minuto**. No hay ningún proceso
que mantener vivo, así que no hay nada que se pueda "caer".

Lo que trae esta actualización, en una línea: **desde el chat de Asistime se
pueden pedir plantillas nuevas y correcciones de diseño, y salen solas en
minutos** — sin que nadie toque código ni despliegue nada.

---

## 1 · Traer el código

**Son dos repos distintos.** El código nuevo vive en `calculadora-asistime`, no
en el repo del worker. Hay que traerlo y copiarlo:

```bash
# 1. traer el código nuevo, a donde sea
git clone https://github.com/Joacogol/calculadora-asistime /tmp/nuevo
cd /tmp/nuevo
git checkout claude/asistime-auto-designs-agent-waais0

# 2. copiarlo sobre el repo del worker
cd /ruta/al/repo/del/worker
cp -r /tmp/nuevo/worker/.claude  .
cp -r /tmp/nuevo/worker/app      .
cp -r /tmp/nuevo/worker/motor    .
cp -r /tmp/nuevo/worker/herramientas .
cp -r /tmp/nuevo/worker/funciones    .
cp -r /tmp/nuevo/worker/estudio      .
cp    /tmp/nuevo/worker/*.sql /tmp/nuevo/worker/*.md .
cp    /tmp/nuevo/worker/requirements.txt .

pip install jinja2
```

`plantilla-generada/` **no se copia**: es documentación —una plantilla de
ejemplo con sus previews— y no forma parte del worker.

Antes de seguir, mirá qué cambió:

```bash
git status
git diff --stat
```

Tiene que tocar `app/`, `motor/`, `herramientas/`, `.claude/skills/`, y agregar
los `.sql`. **Si toca algo que no reconocés, pará y avisá.**

### Sobre la verificación

Hay una herramienta nueva, `verificar-motor.py`, que dibuja todas las
plantillas y avisa si un cambio movió alguna. **Para ESTE despliegue no se
puede usar**, y conviene entender por qué antes de saltearla:

esta actualización pasa las plantillas de estar escritas en Python a ser datos
—HTML + un contrato—. La herramienta sólo sabe dibujar las nuevas, así que no
hay contra qué comparar. La equivalencia de esa migración **ya se verificó
cuando se hizo**, con la misma regla y a mano: 56 renders, byte por byte
idénticos. Está documentado en `APLICAR.md`.

Para el despliegue siguiente y todos los que vengan, sí:

```bash
python3 herramientas/verificar-motor.py boss-padel-disenos --grabar   # ANTES
git pull
python3 herramientas/verificar-motor.py boss-padel-disenos --comparar # DESPUÉS
```

Tiene que decir `120 / 120 idénticas` y tarda unos 150 segundos. Si dice
`DISTINTA`, pará: esa actualización cambia una pieza que ya se estaba usando.
Las imágenes de antes y después quedan en `/tmp/verificar-motor/`.

Para éste, la verificación es la prueba de humo del final.

---

## 2 · Desplegar

```bash
./desplegar-chat.sh
```

Tarda unos minutos (compila la imagen). Va a pedir claves sólo si falta alguna
en Secret Manager; si ya están, no pregunta nada.

Hace cuatro cosas y las va cantando:

| Paso | Qué |
|---|---|
| 1/4 | los secretos de cada cliente (la `service_role` de su Supabase) |
| 1b/4 | la clave de la API de Asistime — **ver la nota de abajo** |
| 2/4 | despliega el job |
| 3/4 | el reloj: una corrida por minuto |

Termina con `▸ 4/4 Listo — clientes: boss-padel-disenos, …`.

> **Si pregunta por la clave de Asistime, no la dejes vacía.** Sin ella el
> worker diseña sin el manual de marca — o sea que las reglas que el club
> escribió desde el chat (precios, qué foto usar, el tono) **no se aplican**.
> Se despliega igual y no se nota hasta que sale una pieza con el precio viejo.

---

## 3 · Las tablas nuevas — una sola vez

En el **SQL Editor del Supabase de Boss**, pegar y ejecutar, en este orden:

1. `plantillas.sql` — las plantillas versionadas
2. `plantilla-pedidos.sql` — la cola de pedidos de plantilla
3. `motor-pedidos.sql` — la lista de pedidos que necesitan código

Los tres se pueden correr aunque ya existan: traen `if not exists` y
`add column if not exists`, así que no rompen nada si se repiten.

> **En un cliente nuevo va uno más, y va primero: `base-de-un-cliente.sql`.**
> Son las cuatro tablas de las que dependen estas tres (`disenos`, `fotos`,
> `cuentas_ig`, `publicaciones`), el bucket `disenos` y sus políticas. Boss y
> Clínica ya las tenían de antes, por eso no aparecen acá arriba. Si se corre
> `plantilla-pedidos.sql` sin él, falla con `function tocar_actualizado() does
> not exist` — que es una forma rara de decir «te faltó el primer archivo».

---

## 4 · Sembrar las plantillas — una sola vez

Sube al Supabase las plantillas que hoy viven sólo en el despliegue, para que
se puedan corregir desde el chat sin volver a desplegar.

```bash
python3 herramientas/sembrar-plantillas.py boss-padel-disenos --probar
python3 herramientas/sembrar-plantillas.py boss-padel-disenos
```

El primero no escribe nada: muestra qué haría. Corré el segundo sólo si lo que
lista tiene sentido.

Usa las mismas variables de entorno que el worker, así que tiene que correr con
el mismo entorno cargado.

---

## 5 · Republicar el catálogo

```bash
ASISTIME_CLAVE=… python3 herramientas/publicar-catalogo.py boss-padel-disenos
```

Es lo que le cuenta al agente qué plantillas existen. Es idempotente: si el
catálogo no cambió, no escribe una versión nueva. **Conviene dejarlo al final
de `desplegar-chat.sh`** para no tener que acordarse.

---

## Verificar que quedó andando

```bash
gcloud run jobs execute boss-chat --region southamerica-east1 --wait
```

Tiene que terminar sin error. En el log vas a ver
`worker arriba · N cliente(s)` y, si no hay nada en la cola,
`sin diseños pendientes, plantillas ni publicaciones en cola`.

Y la prueba de verdad, desde el chat de Asistime:

> «Necesito poder anunciar los cumpleaños en el club: el nombre, la edad y la
> fecha.»

En unos ocho minutos tiene que volver con un preview. Si a los quince no
volvió, mirá el log del job.

---

## Clínica Preventiva — poner su lado a la par

**Clínica ya está andando.** Esta sección queda como registro de qué se hizo, y
como receta para el cliente siguiente. Lo que está hecho:

| | |
|---|---|
| Sus tablas (`plantillas`, `plantilla_pedidos`, `motor_pedidos`) | ✅ |
| `API_CLAVE` en los secretos de sus Edge Functions | ✅ |
| `api-plantillas` (nueva) y `api-disenos` (v7, con el arreglo de WebP) | ✅ |
| Sus 4 plantillas sembradas y publicadas | ✅ |
| Su clave de Asistime en `asistime-api-clinica` | ✅ |
| Catálogo publicado, agente y 6 herramientas | ✅ |

Lo que sigue es cómo se hizo cada paso.

### 1 · Su clave de API

Las Edge Functions leen `API_CLAVE` de un secreto del proyecto, así que cada
cliente tiene **la suya**. Está escrita en el código de sus herramientas de
Asistime; se puede leer desde ahí. **No la pongas en este repo.**

En el panel de Supabase del cliente → *Edge Functions* → *Secrets*, agregá
`API_CLAVE` con ese valor.

> Sin este paso las funciones contestan `500 falta configurar API_CLAVE` y el
> chat no puede pedir nada. Es el único paso que no se puede hacer por comando.
>
> Ojo con el formulario: el campo de arriba es el **nombre** (`API_CLAVE`) y el
> de abajo el **valor**. Cruzarlos deja un secreto llamado como la clave, que
> la función no encuentra.

### 2 · Sus Edge Functions

```bash
cd ~/worker
npx supabase link --project-ref <ref-del-proyecto>
npx supabase functions deploy api-plantillas --no-verify-jwt
npx supabase functions deploy api-disenos    --no-verify-jwt
```

Las dos salen del mismo archivo que está en `funciones/`: no tienen nada
específico de un cliente, leen todo de variables de entorno.

Después conviene probarlas sin gastar un diseño — con la clave del cliente:

```bash
U=https://<ref>.supabase.co/functions/v1/api-plantillas
curl -s -o /dev/null -w "%{http_code}\n" "$U?id=x"                    # 401
curl -s -o /dev/null -w "%{http_code}\n" -H "x-api-clave: $CLAVE" \
     "$U?id=00000000-0000-0000-0000-000000000000"                     # 404
```

Ese par prueba las tres cosas juntas: la clave, el enrutado y que la función
llega a la base. Un `500 falta configurar API_CLAVE` significa que el paso 1 no
está; un `401` con la clave buena, que se coló un salto de línea al pegarla.

### 3 · Sembrarle sus plantillas

```bash
export MARCA=clinica-preventiva-disenos
export BUCKET=disenos
export SUPABASE_URL=https://jejohzzxxnhktdxpdqpy.supabase.co
export SUPABASE_KEY="$(gcloud secrets versions access latest --secret=supabase-key-clinica)"

python3 herramientas/sembrar-plantillas.py clinica-preventiva-disenos --probar
python3 herramientas/sembrar-plantillas.py clinica-preventiva-disenos
```

Tienen que ser **cuatro**: `lateral`, `sangre`, `recorte` y `tipografica`.
`convenio` no aparece y está bien: se quedó escrita en Python porque no es un
diseño con variables sino un programa. Se puede usar para hacer piezas; no se
puede corregir desde el chat.

### 4 · Su clave de Asistime — y por qué no puede ser la de Boss

**La clave de Asistime está atada a un tenant.** Se probó: la de Boss contra un
documento de Clínica contesta `403`. Así que Clínica necesita la suya.

Ya tiene la aplicación creada en su tenant —«Worker de disenos», con los mismos
cuatro permisos de documento que la de Boss— pero **sin ninguna clave todavía**.
Hay que generarla desde Asistime y guardarla:

```bash
read -rs -p "Pegá la clave de Asistime de Clínica y Enter (no se ve): " K; echo
printf '%s' "$K" | gcloud secrets create asistime-api-clinica --data-file=-
gcloud secrets add-iam-policy-binding asistime-api-clinica \
  --member="serviceAccount:worker-boss-padel@boss-padel-disenos.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" --quiet
unset K
```

Nada más: **`desplegar-chat.sh` ya recorre los clientes también para esto**.
Lee de cada `marca.json` qué variable y qué secreto usa esa marca, pide por
teclado la que falte, y las pasa todas al job.

> Antes tenía el secreto de Boss escrito a mano y le pasaba al job una sola
> variable. El efecto era peor que un error: **cada despliegue borraba la clave
> del segundo cliente**, que pasaba a diseñar sin su manual de marca — sin
> fallar y sin avisar, hasta que salía una pieza con un precio viejo.
>
> Si un cliente queda sin su clave, ahora el despliegue lo dice dos veces: en
> el momento y en un resumen al final.

### 5 · Publicarle el catálogo

```bash
ASISTIME_CLAVE_CLINICA="$(gcloud secrets versions access latest --secret=asistime-api-clinica)" \
  python3 herramientas/publicar-catalogo.py clinica-preventiva-disenos --probar
```

Sacale el `--probar` si lo que lista tiene sentido. El nombre de la variable no
es libre: lo declara `marca.json` de cada marca en `asistime.clave_env`.

### 6 · La prueba, desde el chat de Clínica

El agente se llama **Diseñador Clínica Preventiva**. Probá con las dos cosas:

> «Una placa para el carné de salud común a $1490, con resultado en 24 horas.»

> «En la plantilla lateral el precio se ve chico al lado del título, agrandalo.»

La primera tiene que volver con una pieza en dos o tres minutos; la segunda con
un preview de una versión nueva, en borrador, en unos dos.

---

## Stadium — el cliente nuevo, de cero

Stadium es el primero que se armó **entero** con la receta, sin nada previo.
Boss y Clínica ya tenían app, base y usuarios antes de que existiera el motor
de plantillas; Stadium no tenía nada.

Lo que está hecho —y no hay que repetir:

| | |
|---|---|
| Proyecto de Supabase `stadium-disenos` (`heajbidxysjxxegqemka`, sa-east-1) | ✅ |
| Las 7 tablas, el bucket `disenos` y sus políticas | ✅ |
| Kit de marca: `brand.py`, `marca.py`, `marca.json`, logo, tipografías | ✅ |
| 4 plantillas: `precio`, `sale`, `lanzamiento`, `marca` | ✅ |
| Asistime: tenant 176, agente «Diseñador Stadium», 6 herramientas, 2 documentos | ✅ |

Lo que falta, que es lo que necesita una máquina con `gcloud` y `npx`:

### 1 · Su clave de API

Igual que en Clínica: el valor está escrito en el código de sus herramientas de
Asistime (tenant 176) y se lee desde ahí. En el panel de Supabase de Stadium →
*Edge Functions* → *Secrets*, agregar `API_CLAVE` con ese valor. Ojo con el
formulario: arriba el **nombre**, abajo el **valor**.

### 2 · Sus Edge Functions

```bash
cd ~/worker

# El CLI de Supabase busca las funciones en `supabase/functions/<nombre>/` y en
# este repo viven en `funciones/`. Sin estos enlaces el deploy falla con
# «entrypoint path does not exist», que no dice en ningún lado que el problema
# es dónde está el archivo. Se hace una sola vez por máquina.
mkdir -p supabase/functions
for F in api-disenos api-plantillas api-reels; do
  ln -sfn "$PWD/funciones/$F" "supabase/functions/$F"
done

# Y el CLI necesita un token de tu cuenta, que NO es ninguna de las claves de
# los clientes: se saca de supabase.com/dashboard/account/tokens.
read -rs -p "Pegá el token de Supabase y Enter (no se ve): " T
export SUPABASE_ACCESS_TOKEN="$T"; unset T; echo

npx supabase link --project-ref heajbidxysjxxegqemka
npx supabase functions deploy api-plantillas --no-verify-jwt
npx supabase functions deploy api-disenos    --no-verify-jwt
```

Y la prueba de siempre, que no gasta un diseño:

```bash
U=https://heajbidxysjxxegqemka.supabase.co/functions/v1/api-plantillas
curl -s -o /dev/null -w "%{http_code}\n" "$U?id=x"                    # 401
curl -s -o /dev/null -w "%{http_code}\n" -H "x-api-clave: $CLAVE" \
     "$U?id=00000000-0000-0000-0000-000000000000"                     # 404
```

### 3 · Las dos claves en Secret Manager

```bash
read -rs -p "Pegá la service_role key de Stadium y Enter (no se ve): " K; echo
printf '%s' "$K" | gcloud secrets create supabase-key-stadium --data-file=-
unset K

read -rs -p "Pegá la clave de Asistime de Stadium y Enter (no se ve): " K; echo
printf '%s' "$K" | gcloud secrets create asistime-api-stadium --data-file=-
unset K

for S in supabase-key-stadium asistime-api-stadium; do
  gcloud secrets add-iam-policy-binding "$S" \
    --member="serviceAccount:worker-boss-padel@boss-padel-disenos.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" --quiet
done
```

### 4 · Sumarlo a `clientes.json`

`clientes.json` no está en este repo —tiene claves— así que se edita en
`~/worker`. La entrada de Stadium:

```json
{
  "marca":   "stadium-disenos",
  "nombre":  "Stadium",
  "url":     "https://heajbidxysjxxegqemka.supabase.co",
  "key_env": "SUPABASE_KEY_STADIUM",
  "secreto": "supabase-key-stadium"
}
```

Los cinco campos son los que lee `clientes.py`, y **`nombre` no es opcional**:
sin él, `clientes.py json` corta con un `KeyError` en medio del despliegue.
Para comprobar que quedó bien, antes de desplegar:

```bash
python3 clientes.py marcas          # tienen que aparecer los tres
python3 clientes.py run-secrets     # y sus tres secretos
python3 clientes.py asistime        # una línea por cliente con su clave
```

### 5 · Sembrarle sus plantillas y publicar el catálogo

```bash
export MARCA=stadium-disenos
export BUCKET=disenos
export SUPABASE_URL=https://heajbidxysjxxegqemka.supabase.co
export SUPABASE_KEY="$(gcloud secrets versions access latest --secret=supabase-key-stadium)"

python3 herramientas/sembrar-plantillas.py stadium-disenos --probar
python3 herramientas/sembrar-plantillas.py stadium-disenos

ASISTIME_CLAVE_STADIUM="$(gcloud secrets versions access latest --secret=asistime-api-stadium)" \
  python3 herramientas/publicar-catalogo.py stadium-disenos --probar
```

Tienen que ser **cuatro** plantillas. Sacale el `--probar` al último si lo que
lista tiene sentido.

### 6 · Volver a desplegar

```bash
./desplegar-chat.sh
```

Recorre los clientes solo: ve a Stadium en `clientes.json`, encuentra sus dos
secretos ya creados y no pregunta nada.

### 7 · Reels (video por IA)

Ya está hecho: la tabla `reels`, la función `api-reels` desplegada, las tools
`crear_reel` y `estado_reel` en el tenant 176 y enganchadas al agente, y la
configuración en `marca.json` (720p, 6 s, tope 3.000 por pieza y 20.000 al mes
= 2.640 por reel).

Falta:

```bash
# la clave de Magnific para el worker. NO es la del conector: ese entra con
# OAuth de una persona y sirve sólo dentro de un chat.
read -rs -p "Pegá la API key de Magnific y Enter (no se ve): " K; echo
printf '%s' "$K" | gcloud secrets create magnific-api-key --data-file=-
gcloud secrets add-iam-policy-binding magnific-api-key \
  --member="serviceAccount:worker-boss-padel@boss-padel-disenos.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" --quiet
unset K
```

Y montar el secreto en el job, que es lo único que falta después de refrescar
el código —el enganche en el ciclo ya está escrito en `app/chat.py`—:

```bash
gcloud run jobs update disenador-worker --region us-central1 \
  --set-secrets MAGNIFIC_CLAVE=magnific-api-key:latest
```

Verificá que quedó, que es una línea y evita la peor forma de enterarse (un
pedido que se muere recién al pedir el video):

```bash
gcloud run jobs describe disenador-worker --region us-central1 \
  --format='value(spec.template.spec.template.spec.containers[0].env)' | tr ',' '\n' | grep -i magnific
```

La música **no hay que subirla**: la pista `street` viaja en el despliegue,
dentro de `.claude/skills/stadium-disenos/musica/`. El worker la busca ahí
primero y sólo si no está va al bucket. Para agregar una pista nueva sin
desplegar, subila al bucket `disenos` bajo `musica/<clave>.mp3` y agregá la
clave al banco de `marca.json`.

> **El reel se puede probar por partes.** Con `API_CLAVE` puesta y las funciones
> desplegadas, `crear_reel` ya anota la fila y `estado_reel` contesta
> «pendiente»: eso prueba el camino agente → tool → función → base, que es
> donde está casi toda la plomería. El video recién sale cuando el job tenga
> `MAGNIFIC_CLAVE`. Sin ella la fila queda en `pendiente` y el log dice
> exactamente eso: no se gasta nada y no se pierde el pedido.

### 8 · La prueba

El agente es **Diseñador Stadium**. Probá con las dos cosas:

> «Una placa de championes adidas Runfalcon a $3.490, antes $4.990, hasta
> agotar stock.»

> «En la plantilla precio el nombre del producto se ve chico, agrandalo.»

---

## La receta, cuando venga el cliente número cuatro

El orden importa y no es obvio, así que queda escrito:

1. **Supabase**: proyecto nuevo, y en su SQL Editor `base-de-un-cliente.sql`,
   después `plantillas.sql`, `plantilla-pedidos.sql` y `motor-pedidos.sql`.
   El primero tiene que ir primero: los otros tres usan una función que define
   él (`tocar_actualizado`).
2. **Kit de marca** en `.claude/skills/<marca>-disenos/`: `brand.py` (colores,
   CSS y ayudantes), `marca.py` (el contrato del motor), `marca.json` (los
   datos que van al prompt), `SKILL.md`, `assets/`, `fonts/` y las plantillas.
3. **Asistime**: tenant, aplicación con permisos de documento, clave de API,
   los dos documentos (manual de marca y catálogo), las herramientas y el
   agente.
4. **Las claves**: `API_CLAVE` en los secretos de sus Edge Functions,
   `supabase-key-<marca>` y `asistime-api-<marca>` en Secret Manager. Los
   nombres de las dos últimas los declara su `marca.json`.
5. **Sembrar, publicar el catálogo, desplegar.**

Dos cosas que se aprendieron con Stadium y valen para el que sigue:

- **La clave de Asistime es por tenant.** La de otro cliente contesta `403`. No
  se comparte ni por un rato.
- **Comparar la base nueva contra la de referencia, no mirarla.** Se sacó una
  huella de columnas, políticas, triggers, índices, reglas y funciones de
  Clínica y de Stadium, y se compararon. Cuatro de cinco daban igual: la que no
  eran las claves foráneas, a las que les faltaba el `on delete`. Sin esa
  comparación, eso aparecía el día que alguien borrara un usuario y no pudiera.

---

## Lo que NO hace este despliegue

- **No publica ninguna plantilla.** Las que se armen quedan como borrador hasta
  que una persona las apruebe desde el chat.
- **No prende el motorista.** Los pedidos que necesitan código quedan anotados
  en `motor_pedidos`, pero nadie los atiende. Para prenderlo hay que agregar
  `MOTORISTA=1` a las variables del job — y conviene no hacerlo hasta que haya
  alguien mirando las propuestas.

---

## Dos cosas pendientes que no son de este despliegue

**Rotar tres claves.** La de Anthropic (`anthropic-key` en Secret Manager), la
`service_role` de Boss, y la `API_CLAVE` de las Edge Functions.

> **Cuidado con el orden de `API_CLAVE`.** Está escrita en texto plano dentro
> del código de **ocho herramientas de Asistime** —`crear_diseno`,
> `estado_diseno`, `publicar_diseno`, `estado_publicacion`, `crear_plantilla`,
> `estado_plantilla`, `publicar_plantilla` y `avisar_cambio_motor`—. Si se
> cambia el secreto antes de actualizarlas, **se caen las ocho a la vez**.
>
> El orden es: primero las herramientas con la clave nueva, después el secreto.
>
> Y para no confiar en esta lista, que puede quedar vieja: la forma segura de
> encontrarlas todas es buscar los primeros caracteres de la clave actual
> (`705fdf`) en el código de las herramientas del tenant 119.
>
> **`anotar_regla` usa otra clave** (`api-manual`, empieza con `1fe96e`). Es un
> secreto distinto y se rota aparte.

**El disparador.** Existe un servicio (`disparador/`) que enciende el job en el
instante en que entra un pedido, en vez de esperar el minuto. No está
conectado, y no es un olvido: la política de la organización bloquea el webhook
—está anotado en `desplegar-chat.sh`—. Si esa política cambia, se conecta con
`./desplegar-disparador.sh` y el hook que ese script imprime al final.

---

## Si algo sale mal

| Síntoma | Qué mirar |
|---|---|
| `verificar-motor` dice `DISTINTA` | esta actualización cambia una pieza que ya se usaba. Pará y avisá |
| El job falla al desplegar | casi siempre es un secreto que falta; el script dice cuál |
| Un pedido queda `pendiente` para siempre | el reloj no está corriendo: `gcloud scheduler jobs list --location southamerica-east1` |
| Un pedido queda `generando` para siempre | ya no pasa: se rescata solo a los 30 minutos |
| Las piezas salen sin las reglas del club | falta `ASISTIME_CLAVE`. Ver el paso 2 |
