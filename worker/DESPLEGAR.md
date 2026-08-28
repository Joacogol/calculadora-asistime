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
rm -rf /tmp/nuevo
git clone -b claude/asistime-auto-designs-agent-waais0 \
  https://github.com/Joacogol/calculadora-asistime /tmp/nuevo

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
cp    /tmp/nuevo/worker/clientes.py /tmp/nuevo/worker/desplegar-chat.sh .
chmod +x desplegar-chat.sh

pip install jinja2
```

**`clientes.py` y `desplegar-chat.sh` van en la lista, y faltaban.** El
despliegue no es sólo el código que corre en el job: los pasos previos —qué
secretos pedir, cuáles montar— viven en esos dos archivos. Cuando cambia un
paso del despliegue y no se copian, pasa lo peor: el script viejo corre sin
error, dice «Listo», y lo que se desplegó no tiene lo nuevo. Pasó con la clave
de Magnific.

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
| Catálogo publicado, agente y 8 herramientas | ✅ |
| `api-publicar` y las tools de Instagram (27/8/2026) | ✅ |

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
npx supabase functions deploy api-publicar   --no-verify-jwt
```

Las tres salen del mismo archivo que está en `funciones/`: no tienen nada
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

### 6 · Publicar en Instagram — lo que faltaba

**Hecho el 27/8/2026.** Clínica diseñaba bien pero no podía publicar: había que
bajar la pieza del chat y subirla a mano. Boss sí podía, desde el 6/8.

Lo raro es lo poco que faltaba. La base de Clínica ya tenía las dos tablas
(`cuentas_ig` y `publicaciones`) y la vista `instagram_estado`, porque las trae
`base-de-un-cliente.sql`. Y ya tenía **la cuenta conectada y con token válido**
—`clinica.preventiva`, activa—, puesta el 5/8. Lo que no existía era el camino
entre el chat y esa cola: la Edge Function y las dos tools.

| Qué faltaba | Dónde |
|---|---|
| `api-publicar` | Supabase de Clínica |
| `publicar_diseno` y `estado_publicacion` | tenant 73 de Asistime |
| El agente enganchado a esas dos tools | agente 542 |
| La sección «Publicar en Instagram» del prompt | versión 2, publicada |

`api-publicar` **no estaba en el repo**: vivía sólo dentro del Supabase de Boss.
Ahora está en `funciones/api-publicar/`, así que el cliente que viene la recibe
con el resto.

Cómo probarla sin publicar nada —los cinco casos, todos de lectura o de
rechazo—:

```bash
U=https://<ref>.supabase.co/functions/v1/api-publicar
D=<id de un diseño que exista>
curl -s -w " %{http_code}\n" "$U?diseno_id=$D" -H "x-api-clave: mala"     # 401
curl -s -w " %{http_code}\n" "$U" -H "x-api-clave: $CLAVE"                # 400
curl -s -w " %{http_code}\n" "$U?diseno_id=$D" -H "x-api-clave: $CLAVE"   # 200
curl -s -w " %{http_code}\n" -X POST "$U" -H "x-api-clave: $CLAVE" \
     -H "Content-Type: application/json" -d '{}'                          # 400
curl -s -w " %{http_code}\n" -X POST "$U" -H "x-api-clave: $CLAVE" \
     -H "Content-Type: application/json" \
     -d '{"diseno_id":"00000000-0000-0000-0000-000000000000"}'            # 404
```

El último es el que importa y es el menos obvio: un **404** quiere decir que la
función pasó el chequeo de Instagram y se cayó recién al buscar el diseño. Si
en cambio contesta **409 `sin_instagram`**, el token no está o está vencido, y
eso hay que arreglarlo antes de que alguien pida publicar en el chat.

> **El token de Instagram vence.** El de Clínica vence el **4/10/2026**; el de
> Boss, el 2/10. La vista `instagram_estado` los marca `por_vencer` siete días
> antes, pero **nadie mira esa vista**: hay que renovarlos desde la app. Si se
> vencen, `publicar_diseno` contesta que la cuenta no está activa y el agente
> lo dice — no se pierde nada, pero deja de publicar.

### 6b · Subir una foto sin diseñarla

**Hecho el 27/8/2026, después de una prueba que lo dejó a la vista.** Le
pidieron al agente subir una foto a Instagram y el agente **diseñó una placa
con ella**, sin avisar. No era un error del código: `publicar_diseno` sólo
acepta un `diseno_id` —nunca una URL— así que armar una pieza era literalmente
lo único que sabía hacer con una foto. El problema era que lo hacía en
silencio.

Se resolvió con las dos mitades, porque cada una sola deja el agujero abierto:

**La capacidad.** `api-publicar` gana una segunda puerta:

```
POST /api-publicar        una pieza diseñada, por su `diseno_id`
POST /api-publicar/foto   una foto tal cual
```

La foto **no se publica desde la URL que le dicten**. La función la baja,
verifica por sus bytes que sea una imagen de verdad, le saca los metadatos —en
una foto de celular eso incluye dónde se tomó, y acá el archivo sale sin
redibujar— y la guarda en el Storage del cliente. Lo que va a Instagram es
siempre nuestra copia.

Y crea una fila normal en `disenos`, con `estado: listo`. Eso no es un rodeo:
de ahí para abajo funciona todo lo que ya estaba escrito y probado —el freno
de publicar dos veces, la medición de la pieza, la elección entre feed y
story, `estado_publicacion`, el worker— sin que ninguno tenga que saber que
esa pieza no la dibujó nadie. Y deja registro de lo que salió.

> **`medir()` aprendió a leer JPEG.** Sólo sabía PNG, y una foto de celular es
> JPEG: la medición fallaba **en silencio** y se caía a adivinar por el nombre
> del archivo, con lo cual toda foto vertical terminaba clasificada como
> cuadrada e iba al feed recortada. Con piezas del motor nunca se notó porque
> son PNG.

**El prompt.** Versión 3, publicada. Arranca con una regla que ahora encabeza
todo lo demás:

> **Nunca hagas algo distinto de lo que te pidieron sin decirlo.**

Y una tabla que separa los dos caminos por una sola pregunta —*¿hay que
diseñar algo?*—, con la instrucción de preguntar cuando no esté claro en vez
de elegir.

**La tool** es `publicar_foto` (id 2114), enganchada al agente 542.

Probado sin publicar nada real: los cuatro rechazos (sin foto, dirección
interna, una URL que no es imagen, clave mala) y el camino completo
programado para el día siguiente — copió la foto, la midió, la clasificó como
post, encoló, y `estado_publicacion` contestó al instante que estaba
programada en vez de esperar 75 segundos. Después se borró todo.

**En Boss quedó igual, el mismo día.** Se desplegó su `api-publicar` (v7) con
la puerta `/foto` y el texto en la voz del club —«la foto de la cancha», «el
Instagram del club»—, se creó la tool `publicar_foto` (id 2115) y se enganchó
al agente 364, y su prompt subió a la versión 9 con la tabla de los dos caminos
y la misma regla de no hacer otra cosa en silencio.

Una diferencia a propósito: en Boss `publicar_foto` pide `confirmado: true`,
como sus otras dos tools que publican. En Clínica no, porque ahí ninguna lo
pide y meterlo en una sola habría sido una excepción sin explicación. La pausa
existe en las dos — en Clínica la sostiene el prompt.

Probado en Boss igual que en Clínica, sin publicar nada real: sin foto → 400
`falta_la_foto`; una dirección interna → 400 `foto_invalida`; una URL que no es
imagen → 400 `foto_no_sirve`; clave mala → 401; y la puerta vieja intacta → 400
`falta diseno_id`.

> **Falta en Stadium**, y no por el código: su `cuentas_ig` está vacía. Hasta
> que no se conecte el Instagram del club no hay a dónde publicar, así que no
> tiene desplegado `api-publicar` ni sus tools. Cuando se conecte son los
> mismos tres pasos.

---

### 6c · El banco de fotos, y por qué no se podía elegir de él

**Encontrado el 27/8/2026, buscando otra cosa.** Le pidió al agente que la
pieza usara una foto del banco de la clínica y no salía nunca. Tres problemas
apilados, y el orden en que se descubren es el inverso al que importan:

**1 · `crear_diseno` de Clínica no tenía el campo.** Boss lo tenía desde
siempre; la herramienta de Clínica se escribió de cero el 25/8 y quedó sin
`fotos_elegidas`. Sin ese campo no hay forma de nombrar una foto del banco.

**2 · Y el freno que sí tenía la bloqueaba.** Esta guarda:

```js
if (!fotos.length && /\b(foto|imagen|adjunt|...)/i.test(mensaje))
  → 400 "pasame la URL de la foto"
```

miraba sólo `fotos` —las que la persona manda por el chat—. Así que decir
«usá una **foto** del banco» disparaba el freno, y el agente le pedía a la
persona la URL de una foto que la clínica ya tenía guardada. El pedido no
llegaba a salir: en el log de la Edge Function no había **ninguna** llamada
después de las 15:54, mientras seguía intentando.

Es el mismo patrón que el bug del sleep: una guarda que existe para evitar un
caso raro, y que se dispara justo cuando NO debería.

**3 · Y aunque el campo hubiera estado, no había qué elegir.** Las 20 fotos de
la tabla `fotos` tenían `descripcion` y `etiquetas` **vacías**. Como el motor
las traduce a `"Foto que subió el cliente, sin descripción."` / `"uso
general"`, el diseñador veía veinte entradas idénticas con claves como
`whatsapp-image-2026-08-03-at-18-00-49-7`. Y el banco semilla del skill de
Clínica está vacío a propósito, así que el 100% del banco eran esas veinte.

#### Cómo quedó

| Pieza | Qué se hizo |
|---|---|
| `api-disenos` | ruta nueva `GET /api-disenos/banco` (v9 en Clínica) |
| tabla `fotos` | las 20 descritas y etiquetadas, mirándolas una por una |
| tool `ver_banco` (2117) | el agente puede ver el banco antes de encargar |
| tool `crear_diseno` (2063) | campo `fotos_elegidas` + el freno arreglado |
| prompt (v4) | la tabla de los tres caminos de una foto |

El freno sigue existiendo —sin él, una foto que nadie eligió la elige el
diseñador y la pieza sale con otra— pero ahora tiene salida: si el pedido
habla del banco, el error dice «mirá `ver_banco`», no «pasame una URL».

> **Una clave inventada no da error.** El diseñador no la encuentra, elige
> otra foto, y la pieza sale linda con la foto equivocada. Por eso tanto la
> tool como el prompt insisten en copiar la clave tal cual desde `ver_banco`.
> Es la falla más cara del sistema: la que no se ve.

Probado de punta a punta: se encargó una pieza con
`fotos_elegidas: ["whatsapp-image-2026-08-03-at-18-00-49"]` (la fachada), la
columna lo recibió, y la placa salió **con esa foto**. Después se borró.

> **Falta en Boss.** Su `crear_diseno` sí tiene `fotos_elegidas`, pero su
> agente tampoco puede ver el banco: no tiene `ver_banco` ni la ruta `/banco`.
> Y no alcanza con copiar lo de Clínica — la tabla `fotos` de Boss está
> **vacía**: su banco son las ~20 fotos ya descritas a mano en el
> `fotos.json` del skill. Así que su `ver_banco` tiene que leer ese archivo,
> no la tabla. Es un cambio distinto, no una copia.

---

### 6d · Magnific en Clínica: arreglar una foto, o inventarla

**27/8/2026.** Clínica no tenía nada de esto: `api-fotos` no estaba desplegada,
la tabla no existía y su `marca.json` no declaraba el bloque `fotos`, que es el
interruptor que el worker mira para saber si a esa marca le toca la cola.

Y faltaba un verbo. Los cinco que había —`fondo`, `formato`, `tamano`,
`retoque`, `escena`— **parten todos de una foto que ya existe**. Para Stadium
alcanza: tiene una foto por producto y lo que necesita es adaptarlas. Para
Clínica no, y por la razón contraria: tiene veinte fotos y once son casi el
mismo mostrador. Lo que le falta no se resuelve eligiendo mejor.

Así que hay un sexto verbo, `crear`, que no parte de nada:

```
POST /api-fotos  {"verbo":"crear","instruccion":"...","formato":"post"}
```

Le pega a `text-to-image/seedream-v5-pro`, que devuelve un `task_id` y se
consulta igual que los otros cuatro asíncronos. Es el único verbo sin `foto`,
así que esa columna pasó a admitir NULL — la restricción vive en `api-fotos`,
que sabe qué verbo es, y no en la columna, que no lo sabe.

**Cuesta 100 créditos, medidos de verdad**: se generó una imagen y el saldo de
la cuenta bajó de 11.878 a 11.778. No es un número de simulador.

> **Los otros cuatro siguen con la cota de 300.** El simulador del conector ya
> contesta (`images_expand` 50, `images_retouch` 10, `images_upscale` de 90 a
> 1080 según el tamaño) pero **esos son los endpoints del conector, no las
> rutas REST que usa el worker**. Copiarlos sería cambiar una cota honesta por
> una cifra que parece medida y no lo está. Se bajan cuando se midan como se
> midió `crear`: gastando uno y mirando el saldo.

#### El puente con el diseño, que ya existía

No hizo falta plomería nueva. `estado_foto` devuelve la URL de la foto **ya
subida al bucket del cliente** —el worker la baja de Magnific y la guarda,
porque la URL de ellos caduca— y esa URL entra en `crear_diseno` por el campo
`fotos`, el mismo que usan las fotos que manda una persona por el chat. El
agente encadena: `crear_foto` → `estado_foto` → `crear_diseno`.

#### Lo que quedó, y lo que falta

| Pieza | Estado |
|---|---|
| verbo `crear` en `app/fotero.py` | ✅ escrito |
| `api-fotos` con los seis verbos, desplegada en Clínica (v1) | ✅ |
| tabla `fotos_editadas` en Clínica, `foto` nullable | ✅ |
| bloque `fotos` en el `marca.json` de Clínica | ✅ escrito |
| tools `crear_foto` (2118), `editar_foto` (2119), `estado_foto` (2120) | ✅ |
| prompt del agente, versión 5 | ✅ publicada |
| **el worker con el verbo nuevo** | ❌ **falta desplegar** |

El último renglón es el que importa: `fotero.py` y `marca.json` viajan DENTRO
de la imagen del worker. Hasta que no se corra

```bash
cd ~/worker && ./desplegar-chat.sh
```

los pedidos de foto de Clínica se quedan quietos en `pendiente` —no se pierden
ni gastan un crédito— porque el worker todavía no sabe que esa marca edita
fotos. `MAGNIFIC_CLAVE` ya está en el job desde el 26/8, así que el despliegue
no la va a volver a pedir.

Probado hasta donde se puede sin el despliegue: los seis rechazos de la función
(clave mala, verbo inventado, `crear` sin instrucción, formato mal escrito,
`fondo` sin foto, URL interna) y un pedido real que dejó la fila correcta —
`verbo: crear`, `foto: null`, `formato: post`, `pendiente`—. Después se borró.

#### La regla que no es técnica

Una foto inventada que se publica como si fuera la clínica es un problema
distinto al de una pieza fea. Por eso hay tres frenos, y ninguno es opcional:

1. El prompt que va a Magnific pide **sin texto, sin carteles, sin logos**. Una
   fachada generada con un cartel inventado es lo peor que puede salir de acá.
2. `estado_foto` le dice al agente, cuando el verbo fue `crear`, que avise que
   la foto la hizo una IA.
3. El prompt del agente lo repite entre las cosas que no hace nunca: *mostrar
   una foto inventada sin decir que la inventó una IA — ni aunque quede
   perfecta, sobre todo si queda perfecta*.

---

### 6e · Lo mismo en Boss y en Stadium (28/8/2026)

Tres cosas que quedaban abiertas después de Clínica.

#### El banco de Boss, que el agente no podía ver

`crear_diseno` de Boss acepta `fotos_elegidas` desde el primer día, pero nunca
hubo forma de saber **qué claves existen**: el banco de este club son 29 fotos
descritas a mano que viajan dentro de la imagen del worker, en
`referencias/fotos.json`, y el agente del chat no ve ese archivo.

La ruta `/banco` lee la tabla `fotos`, que en Boss estaba **vacía**. Y los
archivos no se podían subir al Storage desde acá: viven adentro del worker, no
en un servidor público.

Así que las 29 filas que se cargaron son el **índice** del banco, no una copia:

| Columna | Qué lleva |
|---|---|
| `clave`, `descripcion`, `etiquetas` | copiadas del `fotos.json` del skill |
| `ancho`, `alto` | medidos de los archivos reales, para que `forma` sirva |
| `url` | **NULL** — el archivo está en el worker, no acá |

`url` pasó a admitir NULL para esto, con un `comment on column` que lo explica.
Y esto **no le cambia nada al diseñador**: `banco.sincronizar()` saltea en
silencio toda fila sin url (`if not clave or not url: continue`), así que sigue
usando los assets del skill exactamente como hasta hoy. El día que Boss suba
fotos desde una app, esas filas sí van a traer url y van a convivir con éstas.

> **Por qué no se subieron los archivos.** Habría unificado los dos bancos, que
> es hacia donde va la arquitectura. Pero cambia lo que el diseñador usa (los
> `assets/banco/` bajados en vez de los del skill), obliga a bajar 29 fotos en
> cada arranque en frío, y necesita la `service_role` de Boss para subirlas. A
> cambio de eso, lo único que se gana es que `/banco` devuelva una url que nadie
> usa. No valía el riesgo sobre algo que hoy anda.

#### `crear_foto` en los tres

| | Clínica | Boss | Stadium |
|---|---|---|---|
| tabla `fotos_editadas` | ✅ | ✅ nueva | ✅ |
| `api-fotos` con los seis verbos | ✅ v1 | ✅ v1 | ✅ v2 |
| bloque `fotos` en `marca.json` | ✅ | ✅ **falta desplegar** | ✅ |
| `crear_foto` / `editar_foto` / `estado_foto` | 2118 / 2119 / 2120 | 2129 / 2130 / 2131 | 2123 / 2079 / 2080 |
| `ver_banco` | 2117 | 2128 | — (su tabla `fotos` está vacía) |

**Cada marca frena una cosa distinta, y no es decoración.** El verbo `crear`
inventa una imagen entera, y lo que es inaceptable inventar cambia por cliente:

- **Stadium** no inventa **productos**. Los championes tienen que ser los de
  verdad; una IA los dibuja *parecidos* y eso es publicidad de algo que no se
  vende. `crear_foto` frena si la descripción nombra un producto y manda a
  `escena`, que parte de la foto real.
- **Boss** no inventa **gente**. Una foto de «nuestros jugadores» hecha por IA
  son personas que no existen presentadas como socios. Frena si la descripción
  pide personas —salvo que diga «sin gente» o «vacía»— y manda al banco, que
  para eso tiene 29 fotos reales.
- **Clínica** no inventa **carteles**: una fachada generada con un cartel que
  dice cualquier cosa es lo peor que puede salir de una cuenta de salud.

Y en los tres, `estado_foto` le dice al agente que avise cuando la foto la hizo
una IA, y el prompt lo repite entre las cosas que no hace nunca.

> **Boss necesita un despliegue del worker.** Su bloque `fotos` en `marca.json`
> viaja dentro de la imagen, igual que pasó con Clínica: hasta que no se corra
> `./desplegar-chat.sh` —copiando antes el código, ver el principio de este
> documento— sus pedidos de foto se quedan quietos en `pendiente`, sin gastar
> un crédito. Stadium y Clínica ya andan.

#### Los cuatro precios, medidos (28/8/2026)

El conector volvió y se midieron los cuatro que faltaban, de la única forma que
vale: corriendo uno y mirando cuánto bajó el saldo.

| Verbo | Cota vieja | Real | |
|---|---|---|---|
| `fondo` | — | **3** | medido el 26/8 |
| `formato` | 300 | **40** | 7 veces más barato |
| `retoque` | 300 | **100** | |
| `escena` | 300 | **100** | mismo endpoint que `retoque` |
| `crear` | — | **100** | medido el 27/8 |
| `tamano` | 300 | **180** | con una foto de 1,9 MP |

Tres de los cuatro salían bastante más baratos de lo que decía la cota, que es
exactamente lo que la cota prometía: equivocarse por arriba y rechazar de más,
nunca dejar pasar un gasto.

**`tamano` es el único que depende del tamaño.** Magnific lo cobra por tramos:
90 el chico, 180 el mediano —el que se midió—, 270 el grande y **1080 el
enorme**. Ese salto es el que puede dejar corta una estimación fija, así que
`_cuerpo` ahora mide la foto y rechaza agrandar una de más de 4 megapíxeles.
No es sólo un freno de costo: agrandar una foto que ya es grande no arregla
nada, porque las piezas se dibujan a 2160.

> **Lo que NO se usó**: los números del simulador del conector. Son de otros
> endpoints con otros modelos que las rutas REST del worker. Por eso los
> precios estuvieron dos días en 300 en vez de tomar prestada una cifra
> parecida — una que parece medida y no lo está es peor que una cota honesta.
> Cuando por fin se midió, `formato` resultó 40 y el simulador decía 50.

---

### 6f · Boss hace video, y nadie tiene ya techo mensual (28/8/2026)

Joaquín le pidió un reel al agente de Boss y no salió. **El agente no falló**:
hizo exactamente lo que su instructivo le decía —«video → `avisar_cambio_motor`»—
y dejó el pedido anotado (`motor_pedidos`, 16:06). El motivo real era más
grande que ese pedido: **Boss no tenía el motor de video prendido para nada**.
Lo tenía Stadium solo.

Y había una trampa al lado: en `crear_diseno` el formato `reel` existe, pero
en el motor de DISEÑOS significa una imagen quieta de 1080×1920 — una story
sin moverse. Si el agente hubiera ido por ahí, habría entregado una placa
llamándola reel. Que dijera «esto necesita código» fue mejor que eso.

**Lo que se hizo, en orden:**

1. **Tabla `reels`** en el Supabase de Boss, copia exacta de la de Stadium
   (23 columnas, 5 constraints, 3 índices, los 2 triggers, RLS). Se copió y no
   se reescribió a propósito: el worker que la atiende es el mismo, así que
   cualquier diferencia sería un bug de un solo cliente.
2. **`api-reels` v1** desplegada en Boss. Probada: 401 con clave mala, 400 con
   clave buena y sin foto.
3. **Bloque `reels` en su `marca.json`** — y esto es lo que hace que el motor
   lo atienda: `reelero.atender` arranca con `if not ficha: return 0`. Sin el
   bloque, un pedido de reel se queda quieto sin gastar un peso. **Por eso el
   despliegue del worker es el que enciende todo esto**, no las Edge Functions.
4. **Plantilla `campana` para Boss** — el motor la exige por nombre para
   dibujar el rótulo que va encima del video, y Boss no la tenía. Sirve además
   como plantilla normal (un anuncio de una idea, sin datos duros).
5. **Tools `crear_reel` (2133) y `estado_reel` (2132)** en el tenant 119, y las
   16 enganchadas al agente 364. **Prompt v11 (4671)** publicado, y corregida
   la descripción de `avisar_cambio_motor`, que seguía mandando el video ahí.

**Sin música, a diferencia de Stadium.** El banco de pistas de Boss está vacío
a propósito: un reel del club sale con el sonido que genera el propio video —la
pelota, la cancha, el ambiente— y para un club deportivo eso suele estar mejor
que una cortina encima. Cuando haya una pista de la casa se agrega en
`reels.musica` con el mp3 en `musica/`, y desde ese momento los reels la llevan.

**Dos reglas nuevas, y las dos son de la casa.** El texto no va DENTRO del
video: el modelo escribe pésimo y saca letras deformadas, así que la escena
va con el cartel vacío y la frase se dibuja encima con `titulo`. Y la gente del
club no se anima: un video le inventa a una persona real gestos y caras que
nunca hizo, así que los reels se arman sobre la cancha, la pelota, un plano
abierto o de espaldas.

#### El techo mensual dejó de existir, en todos

Aparte de los reels, Joaquín pidió sacar el corte mensual de créditos «para
Stadium, Boss, Clínica Preventiva y todos los que se sumen».

No alcanzaba con borrar el número del `marca.json`: el código decía
`... or 20000` y sin la clave caía en el default. Ahora es `or 0` y el corte se
saltea cuando vale 0, así que **sin la clave no hay techo** — que es lo que
hace que un cliente nuevo nazca sin techo sin que nadie se acuerde de nada. Si
alguna vez hiciera falta, se vuelve a escribir `creditos_maximos_mes` en el
bloque y el corte vuelve solo.

**El tope POR PIEZA se queda.** Los dos frenos parecían el mismo y no lo son:
que un pedido salga miles de créditos es un error —un bucle del chat, una
duración absurda— y eso se sigue frenando. Que el mes sume no es un error, es
el cliente usando lo que compró.

> **Lo que NO se pudo probar acá.** Este repo es un espejo PARCIAL del worker:
> no tiene `motor/legibilidad.py`, ni el `brand.py` de Boss, ni sus fuentes.
> (Por eso el despliegue copia con `cp -r`, que fusiona: lo que sólo vive en
> `~/worker` sobrevive.) La `campana` se probó renderizando el Jinja con los
> helpers stubeados —compila, no le falta ninguna variable, y sobre video no
> pinta fondo opaco, que es lo único que taparía el clip entero— pero no se
> dibujó con la tipografía y el logo reales. El primer reel es la prueba.
>
> Y si la `campana` falla, **no se pierde el video**: el rótulo va en su propio
> `try` desde que un reel de 4.400 créditos murió así. Sale el clip sin texto y
> la nota dice por qué; `estado_reel` se la lee a la persona antes de que suba.

---

### 7 · La prueba, desde el chat de Clínica

El agente se llama **Diseñador Clínica Preventiva**. Probá con las dos cosas:

> «Una placa para el carné de salud común a $1490, con resultado en 24 horas.»

> «En la plantilla lateral el precio se ve chico al lado del título, agrandalo.»

La primera tiene que volver con una pieza en dos o tres minutos; la segunda con
un preview de una versión nueva, en borrador, en unos dos.

Y la tercera, **una vez que la primera volvió y la miraste**:

> «Publicala.»

Tiene que quedar en cola y salir en el Instagram de la clínica en un par de
minutos, con el link del posteo. Ojo con dos cosas al leer la respuesta:

- **«Quedó en cola» no es «salió».** El agente tiene que confirmarlo con
  `estado_publicacion` antes de decir que está publicado. Si dice que salió sin
  haber confirmado, el prompt no está tomando — revisá que la versión 2 sea la
  publicada.
- **Si la pieza tiene un post y una story**, el agente tiene que preguntarte
  cuál querés antes de publicar, no elegir por su cuenta.

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
for F in api-disenos api-plantillas api-publicar api-reels api-fotos; do
  ln -sfn "$PWD/funciones/$F" "supabase/functions/$F"
done

# Y el CLI necesita un token de tu cuenta, que NO es ninguna de las claves de
# los clientes: se saca de supabase.com/dashboard/account/tokens.
read -rs -p "Pegá el token de Supabase y Enter (no se ve): " T
export SUPABASE_ACCESS_TOKEN="$T"; unset T; echo

npx supabase link --project-ref heajbidxysjxxegqemka
npx supabase functions deploy api-plantillas --no-verify-jwt
npx supabase functions deploy api-disenos    --no-verify-jwt
npx supabase functions deploy api-publicar   --no-verify-jwt
```

> `api-publicar` se despliega igual aunque Stadium **todavía no tenga Instagram
> conectado**: sin cuenta contesta `409 sin_instagram` y no rompe nada. El día
> que se conecte, la función ya está y sólo faltan las dos tools. Stadium
> tampoco las tiene todavía: hoy su agente diseña y edita fotos, no publica.

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
configuración en `marca.json`.

**Qué modelo se usa y cuánto sale.** Hay tres calidades, y la persona la puede
pedir en el chat («esto es una prueba», «esto va a publicarse»); el worker la
lee del mensaje. Precios medidos con `simulate_cost` el 26/8/2026, para 10
segundos en vertical:

| Calidad | Modelo | Créditos |
|---|---|---|
| `borrador` | Seedance 2.0 Mini 480p | 700 |
| `normal` ← el default | Seedance 2.0 Mini 720p | 1.400 |
| `maxima` | Seedance 2.5 720p | 4.400 |

Los modelos NO son intercambiables y por eso el worker guarda de cada uno qué
acepta: Mini hace 5 o 10 segundos exactos —nada en el medio—, no tiene el campo
`multishot` (los planos se pliegan a un prompt numerado) y no acepta que le
pidan silencio, así que su audio propio no se mezcla debajo de la música de la
marca. 2.5 hace de 4 en adelante y acepta todo.

Si lo pedido no entra en `creditos_maximos`, el worker **no rechaza de
entrada**: primero busca la combinación más cercana que sí entre —cuidando
antes la duración que la calidad, porque cuatro segundos donde se pidieron diez
se notan y el cambio de modelo mucho menos— y deja escrito en `notas` qué
cambió. Sólo rechaza si ni el más barato entra.

El enganche en el ciclo del worker ya está escrito (`app/chat.py` llama a
`reelero.atender`), y la música también viaja con el despliegue: la pista
`street` vive en `.claude/skills/stadium-disenos/musica/`. El worker la busca
ahí primero y sólo si no está va al bucket. Para agregar una pista nueva sin
desplegar, subila al bucket `disenos` bajo `musica/<clave>.mp3` y agregá la
clave al banco de `marca.json`.

Falta una sola cosa: **la clave de Magnific en el job**. Y no hay que correr
nada aparte — `desplegar-chat.sh` la pide solo, porque `stadium-disenos`
declara el bloque `reels`:

```bash
cd ~/worker && ./desplegar-chat.sh
```

En el paso `1c/4` va a decir «La clave de Magnific (reels de video) — la
piden: stadium-disenos» y pedirla sin eco. Se guarda en Secret Manager como
`magnific-api-key` y entra al job como `MAGNIFIC_CLAVE`. Los despliegues que
vengan después ya no la van a pedir.

**No es la del conector de Magnific**: ese entra con OAuth de una persona y
sirve sólo adentro de un chat. El worker corre solo y necesita llave propia.

Si la dejás vacía el despliegue sale igual y no se rompe nada: el worker mira
la clave ANTES de tocar una fila, así que los pedidos de reel se quedan quietos
en `pendiente`, no se gasta un crédito, y salen solos en la primera corrida
después de cargarla. En el log se ve así:

```
[stadium-disenos] 1 reel(s) esperando: falta MAGNIFIC_CLAVE en el job
```

> **El reel se puede probar por partes.** Con `API_CLAVE` puesta y las funciones
> desplegadas, `crear_reel` ya anota la fila y `estado_reel` contesta
> «pendiente»: eso prueba el camino agente → tool → función → base, que es
> donde está casi toda la plomería. El video recién sale cuando el job tenga
> `MAGNIFIC_CLAVE`.

Un reel tarda unos cuatro minutos y el job vive uno, así que la fila cruza
cuatro o cinco corridas: `pendiente → generando → montando → listo`. Para
mirarla de afuera:

```sql
select estado, tarea, creditos_estimados, notas, url
from reels order by creado_en desc limit 5;
```

### 7b · Editor de fotos (los cinco verbos)

La tabla `fotos_editadas` está creada en Stadium, `api-fotos` desplegada
(versión 1) y `app/fotero.py` enganchado al ciclo. Falta **crear las dos tools
en Asistime**, con la misma clave que ya usan `crear_reel` y `estado_reel`.

Los verbos, y de dónde salió cada uno:

| Verbo | Qué hace | Por qué está |
|---|---|---|
| `fondo` | recorta el producto | la foto de catálogo viene sobre blanco y `campana` tiene escrito que eso «obliga a un velo tan grande que la pieza sale gris» |
| `formato` | la lleva a otra proporción | hay una foto por producto y cuatro formatos; recortar a 9:16 se come el producto, así que **expande** en vez de recortar |
| `tamano` | la agranda | el cliente manda 800 píxeles por WhatsApp y las piezas se dibujan a 2160 |
| `retoque` | saca o cambia algo puntual | «sacale el cartel de oferta», «borrá la persona del fondo» |
| `escena` | pone el producto en otro lugar | una calle, una mesa, un pie |

`retoque` y `escena` son el mismo endpoint con distinto prompt, y los dos
GENERAN imagen: pueden deformar el producto. Por eso el worker le pega a cada
prompt una regla de que el producto no se toca —misma forma, mismos colores,
mismos logos—, la misma lección que dejaron los reels. Aun así, una pieza que
sale de `escena` conviene mirarla antes de publicarla.

**Los precios.** `fondo` son 3 créditos, medido. Los otros cuatro **no se
pudieron medir** —el conector de Magnific, que es donde vive el simulador, se
cayó a mitad de camino— así que el worker les pone una cota alta de 300 en vez
de una estimación: si el número está mal, está mal por arriba, y eso rechaza
algo que entraba en lugar de dejar pasar un gasto. Cuando se puedan medir hay
que bajarlos en `app/fotero.py`.

**Las tools en Asistime ya están creadas** (tenant 176, ids 2079 y 2080) y
enganchadas al agente Diseñador Stadium:

- `editar_foto` → `POST` a `.../functions/v1/api-fotos` con
  `{verbo, foto, instruccion?, formato?}`. Devuelve un id al instante.
- `estado_foto` → `GET` a `.../functions/v1/api-fotos?id=...`. **Espera hasta
  45 segundos adentro** antes de contestar: una edición tarda segundos, así que
  la mayoría de las veces el agente puede mostrar la foto en el mismo mensaje
  en vez de decir «ya te la mando». Con `&esperar=no` contesta al instante.
  Por eso esta tool NO tiene bucle de espera propio, a diferencia de
  `estado_diseno` y `estado_reel`: esperar de los dos lados no acorta nada y
  hace el camino más difícil de razonar.

**El prompt del agente se reescribió** (versión 2, publicada). Además de los
reels y las fotos, arregla algo que estaba roto desde que se rehízo el set de
plantillas: la versión 1 nombraba `sale`, `lanzamiento` y `marca`, que ya no
existen. Ahora nombra las cinco reales y dice explícitamente que **si el
catálogo y el prompt no coinciden, manda el catálogo** — el catálogo lo genera
el motor solo y no se puede quedar viejo; el prompt sí.

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
6. **Instagram, si el cliente lo quiere**: conectar la cuenta (queda en
   `cuentas_ig`), desplegar `api-publicar` y crear las tools `publicar_diseno`
   y `estado_publicacion` en su tenant. Es lo último a propósito: publicar en
   la cuenta real de un cliente no se deshace, y conviene que antes haya
   piezas que alguien ya miró y aprobó.

Dos cosas que se aprendieron con Stadium y valen para el que sigue:

- **La clave de Asistime es por tenant.** La de otro cliente contesta `403`. No
  se comparte ni por un rato.
- **Que la tabla exista no es que la función exista.** Clínica tuvo desde el
  primer día las tablas de publicación y la cuenta de Instagram conectada, y
  aun así no podía publicar: faltaban la Edge Function y las tools, y
  `api-publicar` ni siquiera estaba en el repo — vivía sólo dentro del Supabase
  de Boss. Cuando algo «anda en un cliente y no en otro», el primer lugar donde
  mirar es qué hay desplegado, no qué hay en la base.
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

## El sandbox de las tools de Asistime no sabe dormir

Vale para cualquier tool que se escriba de acá en adelante, así que va escrito
donde se lee y no en un comentario.

**Una tool de Asistime no puede esperar.** Esto:

```js
await new Promise(function (seguir) { setTimeout(seguir, 8000); });
```

no la suspende ocho segundos: la **mata**, y el chat contesta un error.

Las cuatro tools de estado —`estado_diseno`, `estado_plantilla`,
`estado_publicacion`, `estado_reel`— estaban escritas con un bucle que
consultaba, y si todavía no estaba listo dormía y volvía a consultar. Ese
bucle sale por `break` cuando la pieza **ya está**, o sea antes de llegar al
sleep. Así que fallaba **únicamente cuando la pieza no estaba lista** — que es
exactamente el caso para el que el bucle se había escrito.

Andaba siempre que no hiciera falta. Por eso sobrevivió a 22 diseños seguidos
en Clínica: cada vez que el agente consultó, la placa ya estaba.

Se descubrió el **27/8/2026**: una consulta que llegó **nueve segundos** antes
de que la placa terminara. La placa salió perfecta y el chat dijo que había
fallado. Lo que lo delató fue el log de la Edge Function: **una sola llamada**
donde tenía que haber diez.

### Cómo queda

| Dónde | Qué hace |
|---|---|
| La Edge Function (`GET`) | **espera adentro** 55 s (75 s en `api-publicar`) |
| La tool de Asistime | **una sola consulta**, sin bucle y sin `setTimeout` |

Si al volver no está listo, la tool devuelve `listo: false` con un mensaje que
le dice al agente que **no es un error** y que vuelva a llamar. Encadenando
tres o cuatro consultas se cubren los 2 a 4 minutos de una pieza sin que el
chat conteste nunca un error.

Todas las funciones aceptan `?esperar=no` para saltear la espera — sirve para
probarlas a mano sin quedarse un minuto mirando el cursor.

### Dónde quedó aplicado (27/8/2026)

| Cliente | Funciones redesplegadas | Tools corregidas |
|---|---|---|
| Clínica (73) | `api-disenos` v8, `api-plantillas` v5, `api-publicar` v2 | `estado_diseno` 2064, `estado_plantilla` 2061, `estado_publicacion` 2109 |
| Boss (119) | `api-disenos` v9, `api-plantillas` v6, `api-publicar` v6 | `estado_diseno` 1665, `estado_plantilla` 2056, `estado_publicacion` 1666 |
| Stadium (176) | `api-disenos` v2, `api-reels` v4, **`api-plantillas` v1 (no existía)** | `estado_diseno` 2070, `estado_plantilla` 2072, `estado_reel` 2076 |

`estado_foto` de Stadium ya estaba bien: se escribió sin bucle porque
`api-fotos` esperaba adentro desde el primer día. Es el único que nunca
estuvo roto, y por la razón correcta.

> **A Stadium le faltaba `api-plantillas` entera.** No estaba desplegada — la
> función nunca se había subido a su proyecto. Sus cuatro tools de plantilla
> (`crear_plantilla`, `estado_plantilla`, `publicar_plantilla` y
> `avisar_cambio_motor`, que entra por `/motor`) apuntaban a una URL que daba
> 404. Nadie lo notó porque en Stadium todavía nadie había pedido una
> plantilla nueva. Sus tablas sí estaban: lo único que faltaba era el
> despliegue. Ya está, y probada.
>
> La lección es la misma que con `api-publicar` en Clínica: **que la tabla
> exista no es que la función exista**, y una tool que apunta a una función
> que no está no se queja hasta que alguien la usa.

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
