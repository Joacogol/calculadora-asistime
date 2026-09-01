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

Antes de seguir, comprobá que la copia quedó completa:

```bash
diff -rq /tmp/nuevo/worker/motor motor
diff -rq /tmp/nuevo/worker/app   app
```

**Los dos tienen que imprimir nada**: eso significa que lo que quedó en el
worker es exactamente lo que se subió.

> Acá decía `git status` y `git diff --stat`. **No sirve: `~/worker` no es un
> repositorio de git**, así que esos dos comandos contestan `fatal: not a git
> repository` y no comprueban nada. Se descubrió el 31/8/2026, desplegando.
> `diff -rq` hace la comprobación de verdad —compara archivo por archivo contra
> el origen— y encima no depende de que el worker sea un repo.

Y el control que de verdad importa cuando el despliegue cambia el script: que
lo nuevo esté en el archivo que se va a ejecutar. Por ejemplo, para el cambio
de máquina del 31/8:

```bash
grep "cpu 8" desplegar-chat.sh
```

Si no imprime nada, el `cp` del script no funcionó: el despliegue va a correr,
decir «Listo», y no traer lo nuevo. **Parar ahí.**

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

### 6g · Publicar el video: al feed o de story (28/8/2026)

Joaquín le pidió al agente de Boss publicar una story de un video y le dijo que
no podía. **Y era verdad, porque yo se lo había escrito en el instructivo.**
Pero la razón que yo suponía —que faltaba la espera de transcodificación de
Instagram— era falsa. Vale anotarlo: se afirmó sin medir.

**El worker sabía hacerlo desde siempre**, y con cuidado:

- `publicador.py` ya elegía el contenedor: `if _es_video(pieza): return
  ig.contenedor_story(pieza, es_video=True)`.
- `instagram.py` ya tenía las dos ramas de `contenedor_story` (`video_url` o
  `image_url`) y `contenedor_reel` con `share_to_feed`.
- Y la espera **está escrita**: `ig.esperar(contenedor)` con reintentos hasta
  una hora, contados en `esperas` y no en `intentos` a propósito, para que
  aguantar un video no se confunda con haber fallado.

Lo que faltaba estaba todo en la puerta de entrada, `api-publicar`:

1. **`publicar_diseno` lee `disenos`.** Un reel de `crear_reel` vive en `reels`
   y no lo veía nadie. Ahora hay una ruta `/reel` que lo anota como un diseño
   de un solo video — **el mismo truco que `/foto`**, para que el freno de
   publicar dos veces, la consulta de estado y el worker sigan funcionando sin
   enterarse de que la pieza salió de otra tabla. El video NO se copia: ya está
   en nuestro bucket.
2. **Un video sólo se ofrecía como `reel`, nunca como `story`.** Eran dos
   líneas. Ahora, cuando hay video, se ofrecen las dos y el agente **pregunta**:
   son publicaciones distintas —el reel queda en la grilla, la story se va en
   24 horas— y elegir por la persona sería adivinar.

**Reusar el diseño sintético no es una optimización.** Si cada llamada creara
uno nuevo, el freno de «ya se publicó» —que mira por diseño— nunca se
dispararía y dos llamadas seguidas serían dos posteos. Por eso la ruta busca
primero por la marca `[reel <id>]` que deja en el `mensaje`.

En Asistime: tool **`publicar_reel` (2134)**, 17 enganchadas al agente 364, y
**prompt v12 (4675)**.

> **Nunca se publicó un video por este sistema.** Se miraron las publicaciones
> de los tres clientes: seis en total, las seis imágenes. O sea que este camino
> no estaba roto, estaba **sin estrenar** — y el primer reel que se suba es la
> prueba de verdad de todo lo de arriba.

---

### 6h · El primer intento de publicar el reel, y el error que mentía

Joaquín pidió subir su reel como story y le saltó un error. El log de la
función lo dice en una línea:

```
GET | 400 | .../rest/v1/reels?id=eq.Prop_plane_flying_with_banner_202608281431.mp4
```

**El agente mandó el nombre del archivo en vez del id del reel.** PostgREST
rechazó eso porque no es un uuid, devolvió 400, y de ahí salía mi mensaje:
«Esta marca no hace reels, así que no hay ninguno para publicar».

Ese mensaje es el verdadero problema. **Es falso** —Boss hace reels, el video
estaba hecho y pago— y manda a mirar al lugar más equivocado posible: a la
configuración de la marca, cuando lo que estaba mal era un parámetro. Un error
que apunta al lugar equivocado cuesta más que no tener error.

Dos arreglos, en dos capas:

1. **En la tool `publicar_reel`**: el id se valida como uuid ANTES de salir a
   la red, y el mensaje le dice al agente exactamente qué mandó mal y dónde
   está el id bueno. Se arregla solo, sin que nadie mire un log.
2. **En `api-publicar`**: el mismo guardián, y el `!rr.ok` dejó de afirmar que
   la marca no hace reels. Ahora es un 502 que dice que no se pudo buscar y
   que puede ser de las dos cosas, sin elegir una y equivocarse.

> **La lección, que ya está escrita en otros lugares de este repo.** Un
> guardián que se dispara sólo en el caso raro es el que nunca se prueba, y
> el que va a mentir justo cuando alguien lo necesite. Éste se escribió el
> mismo día que la función y falló en el primer uso real.

---

### 6i · Adjuntar un archivo y decir «subilo» (28/8/2026)

Lo que Joaquín quería desde el principio, y que yo entendí tarde: **adjuntar
un archivo propio en el chat y publicarlo tal cual.** No generar nada. Todo lo
de las secciones anteriores publica videos que hace NUESTRO motor, que es otra
cosa.

Eso no existía para video en ningún cliente. `publicar_foto` mira los bytes y
acepta sólo JPG, PNG y WebP, así que un mp4 devolvía «eso no es una imagen que
Instagram acepte». (Se revisó: Clínica tampoco lo tenía. Los dos clientes
tienen la misma puerta, y la de Clínica es una versión más vieja todavía.)

**La puerta `/foto` ahora acepta las dos cosas** y decide por los bytes: la
caja `ftyp` de los primeros doce dice si es MP4 o MOV. Sigue llamándose
`/foto` por historia; el campo nuevo es `archivo` y el viejo sigue andando.

Tres decisiones que vale la pena entender:

- **Se asoma antes de bajar.** Un `Range` de 64 KB alcanza para saber qué es, y
  el `content-range` de esa misma respuesta trae el tamaño total. Traer
  cincuenta megas para descubrir que no servían es pagar el viaje entero por
  una pregunta de doce bytes. Si el servidor ignora el `Range` y manda todo, se
  lee el primer pedazo y se corta la conexión.
- **El video se copia, pero en flujo.** `body: rv.body` en vez de un
  `arrayBuffer`: el archivo pasa de una punta a la otra sin quedar entero en la
  memoria de la función. Y se copia, en vez de publicar la URL del chat, por lo
  mismo que la foto — esa URL se vence, e Instagram tarda en procesar un video.
- **No se re-empaqueta.** Un video no lleva las coordenadas del celular como
  una foto, y recodificarlo acá sería tardar minutos para empeorar la imagen.
  Tope de 80 MB.

En Asistime: **`publicar_archivo` (2138) reemplaza a `publicar_foto`** y queda
enganchada en su lugar. No conviven: dos puertas para el mismo trabajo es
exactamente lo que hace que un agente elija mal. **Prompt v13 (4682)**, que
ahora arranca con la pregunta que ordena todo lo demás — *¿hay que diseñar
algo?* — y con la instrucción de preguntar en vez de elegir.

> `publicar_foto` (2115) queda existiendo pero desenganchada, por si hay que
> volver atrás. Cuando pase un tiempo sin sustos, se borra.

---

### 6j · Una regla que está SUPUESTA y no medida (28/8/2026)

En el prompt de Boss v11 escribí, como si fuera un hecho:

> «El modelo de video escribe pésimo: si le pedís un cartel que diga algo,
> salen letras deformadas y palabras inventadas.»

**Eso no se midió nunca.** Era una creencia general sobre modelos de video
aplicada a Seedance 2.0 Mini sin una sola prueba. Queda anotado acá porque en
este repo la diferencia entre «se midió» y «se supone» es la que sostiene todo
lo demás, y ésta se coló del lado equivocado.

Dos cosas la ponen en duda:

1. **El motor NUNCA prohibió el texto.** El único `"no text"` del código está
   en `_planos()`, la lista de planos de emergencia que se usa sólo si falla el
   guión. El camino normal —`motor/guion.py`— no dice nada del asunto. O sea
   que el pedido de un cartel le habría llegado a Seedance tal cual: lo único
   que lo frenaba era mi instrucción al agente de no pedirlo.
2. **Joaquín lo hizo por fuera y salió.** El 28/8/2026 armó la misma avioneta
   con el cartel en Nano Banana (modelo Omni) y el texto salió legible.

Eso NO prueba que Seedance lo haga —es otro modelo— pero sube las chances lo
suficiente como para que medirlo sea más barato que seguir suponiendo.

**Cómo se mide, cuando alguien quiera:** un reel en calidad `borrador` (700
créditos, la mitad de uno normal) pidiendo el cartel escrito dentro de la
escena. Si las letras salen bien, se saca la regla del prompt; si salen
deformadas, la regla se queda pero por fin con una medición atrás.

> **El camino que probablemente sea el mejor de los tres.** Que el cartel venga
> ya escrito en la FOTO DE PARTIDA —los modelos de imagen escriben bastante
> mejor que los de video— y que el video sólo tenga que conservarlo en vez de
> inventarlo. Hoy está cerrado porque `_prompt("crear")` en `fotero.py` le pega
> atrás «No text, no letters, no logos, no signage» a toda foto inventada. Esa
> prohibición tiene una razón buena y NO se saca a lo bruto: un cartel
> inventado en la fachada de una clínica es un problema de verdad. Pero es una
> regla que podría vivir en el `marca.json` de cada cliente en vez de estar
> clavada en el código para todos.

---

### 6k · El catálogo decía que faltaba una plantilla que no hacía falta (28/8/2026)

Se pidió un carrusel de seis diapositivas para el servicio de Papanicolaou y el
agente de Clínica contestó que **no existe una plantilla de carrusel** y ofreció
armar una.

**El agente no se portó mal**: buscó, leyó el catálogo, no encontró `carrusel`,
aplicó la regla de «si falta, armala» y preguntó antes de gastar. Hizo todo bien
con la información que tenía. La información estaba mal.

Un carrusel **no es una plantilla, es un formato**. Lo arma el motor encadenando
diapositivas con la `portada` y el `cierre` que la marca ya tiene en `DIAPOS`.
Y estaba a mano:

- `crear_diseno` de Clínica **ya acepta** `carrusel` en sus formatos válidos, y
  su propia descripción pone de ejemplo «un carrusel explicando el psicotécnico».
- Clínica **ya lo había hecho**: el 4/8/2026, dos piezas de 3 y 4 imágenes
  pedidas como «Necesito un carrusel con estos 3 slides», con formato
  `secuencia`. Las dos salieron bien.

El catálogo listaba sólo plantillas de UNA pieza y nunca decía que los formatos
encadenados existen por otro lado. Y remataba con un renglón que empujaba en la
dirección contraria: «`avisar_cambio_motor` queda para… **la estructura del
carrusel**».

**Arreglado en dos lugares:**

1. `motor/plantillas.py` — el generador del catálogo gana una sección entera,
   «Un carrusel NO necesita una plantilla de carrusel», y el renglón final deja
   de nombrar el carrusel entre lo que necesita código.
2. **El documento de Asistime, a mano** (tenant 73, doc 832, versión 2
   publicada). No es lo mismo que lo anterior: el generador arregla el problema
   *desde el próximo despliegue*, y esto lo arregla *ahora*. Cuando se despliegue,
   `publicar-catalogo.py` lo va a pisar con el mismo texto y las dos versiones
   convergen.

> **Boss y Stadium tienen el mismo renglón equivocado** en su catálogo. Ahí no
> se editó a mano porque nadie chocó todavía; el despliegue del generador los
> corrige a los tres.

**La lección.** El catálogo se genera solo desde los contratos de las plantillas
—que es lo que lo mantiene al día— pero por eso mismo sólo puede hablar de
plantillas. Todo lo que el motor sabe hacer y NO es una plantilla es invisible
ahí, y el agente no tiene forma de enterarse. Los formatos encadenados eran el
primer caso; conviene mirar si hay otros.

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

## El texto que no entra (31/8/2026)

Una placa de Clínica salió con **«PAPANICOLAOU» cortado contra el borde
derecho**. Es el peor tipo de error de este sistema: la pieza se dibuja bien en
todo lo demás, se publica igual que una correcta, y quien la descubre es el
cliente en su propio feed.

**No era un caso nuevo.** El 25/8 quedó anotado en los pedidos al motor que
tres plantillas de Boss resolvían el mismo problema por su cuenta, cada una a
su manera, y que hacía falta una sola forma de decir «este texto entra en esta
caja». Nunca se construyó. Seis días después salió esto.

**Por qué la plantilla no lo agarró aunque ya tenía su propio ajuste.** La
`lateral` de Clínica llama a `achicar_titular(d.titulo, m.cuerpo)`, que decide
por la **cantidad de letras** del título. «PAPANICOLAOU» tiene doce, que a esa
cuenta le parecen pocas, así que lo dejó en 76 px. Pero son doce mayúsculas de
una sola palabra —sin ningún lugar donde cortar el renglón— en un panel de
480 px de ancho útil: se pasaban 115. Contar letras nunca iba a ver eso.

**Dónde quedó el arreglo.** En `motor/render.py`, dentro de `Render._captura`,
que es el cuello por el que pasa **toda** pieza de **toda** marca: una placa,
una diapositiva de carrusel, una de secuencia, y también la vista previa que
mira el diseñador cuando está creando una plantilla (`app/plantillero.py` llama
al mismo `_captura`). No hay ninguna marca ni ningún formato que lo esquive, y
no hay nada que una plantilla nueva tenga que acordarse de hacer.

Con las fuentes ya cargadas y antes de sacar la foto, mide el texto **dibujado**
y, si se sale, lo achica de a 4 % hasta que entre. Si llega al piso (55 % del
tamaño original) y todavía se sale, **levanta `TextoNoEntra` y la pieza no se
guarda**. Una placa con el título cortado no se publica.

### Las tres decisiones, y por qué son ésas

**Se mide la tinta, no la caja.** Con `Range.selectNodeContents()` y no con el
rectángulo del elemento. Es exactamente el caso que falló: una palabra larga
sin dónde cortar se desborda de su caja, pero la caja sigue midiendo lo que
decía el CSS. El rectángulo habría dicho que estaba todo bien.

**El límite es el lienzo, no la caja del contenedor.** Se probó con la caja
—el interior del contenedor, ya sin padding— y hubo que descartarla midiendo:
de las quince piezas reales de Stadium (cinco plantillas por tres formatos),
**las quince** se pasan de su caja por arriba o por abajo, entre 1 y 37 px,
porque la caja de línea incluye ascendentes y descendentes que un interlineado
de 0.84 recorta a propósito. Con ese límite el motor achicaba «$ 3.990» de
118 px a 64 y arruinaba piezas que estaban bien.

**El margen de seguridad es de 16 px y sólo a los costados.** La tinta que toca
el filo se lee como cortada aunque técnicamente entre. En esas mismas quince
piezas, el texto que más se arrima a un costado queda a 21 px, así que 16 no
toca nada. Verticalmente el límite es el borde pelado: ahí hay texto legítimo a
13 px del borde de abajo, y exigir aire vertical es pelearse con la tipografía.

### Cómo se probó

| Prueba | Resultado |
|---|---|
| Las 15 piezas reales de Stadium, por el camino real | 15 dibujadas, **ninguna tocada, ninguna rechazada** |
| «PAPANICOLAOU» en la geometría exacta de la `lateral` | se salía 115 px → de 76 px a 62 px, **entra** |
| «Carné de salud» y «En el día», mismo panel | entran solas, el guardián no las toca |
| Una sola palabra imposible de 21 letras | achica al piso, sigue afuera → **rechazada** |
| La salida por línea de comandos al rechazar | código 2 y una frase, no un traceback |

La geometría de la prueba no está inventada: sale del contrato de la `lateral`
v1 publicada en el Supabase de Clínica —panel 56 % de 1080, padding 58/62,
cuerpo 76—. La tipografía de Clínica no está en este repo, así que se usó
Archivo variable en peso 900, que es la misma familia.

**Un efecto de borde bueno:** el guardián corre también en la vista previa de
`crear_plantilla`. Una plantilla nueva que apriete demasiado el título se lo
dice al diseñador mientras la está haciendo, no al cliente en su feed.

**Lo que este arreglo NO hace:** no reacomoda el diseño. Achica y, si no
alcanza, se planta. «PAPANICOLAOU» entra pero queda más cerca del borde de lo
que el padding del panel pedía —entero y legible, pero apretado—. Que la
plantilla acomode mejor un título de una sola palabra larga es trabajo de la
plantilla; que no salga cortado ya no depende de que nadie se acuerde.

---

## Reels con material propio (31/8/2026)

Pedido de Joaquín: «poder adjuntarle videos y que los pegue en base a lo que
hay, y le agregue los subtítulos».

**La mitad ya estaba construida y desconectada.** `motor/video.py` y
`motor/guion.py` son unas 1.400 líneas de editor de verdad: corta un clip desde
el segundo que se le diga, le cambia la velocidad con cámara lenta bien hecha,
lo encuadra en 9:16 de tres maneras, pega los tramos y mezcla el audio con
efectos. Hasta valida el guion ANTES de encodear, que es lo caro. Y
`desde_guion` decía en su propio docstring **«es la puerta que usa el agente»**
— pero ningún módulo de `app/` la importaba. Nadie la llamó nunca.

**La otra mitad era un bug mudo.** `guion.py` declara `subtitulos` en su
contrato y los valida con cuidado. `a_spec` no los copiaba al spec. O sea: el
agente escribía subtítulos, el validador los aceptaba, y no aparecían en el
video, sin ningún error que lo explicara.

### Los dos caminos, y por qué están separados

| | `crear_reel` | `montar_reel` |
|---|---|---|
| De dónde sale el video | una IA lo INVENTA a partir de una foto | se EDITA material que ya existe |
| Qué cuesta | miles de créditos | **cero** |
| Cuánto tarda | unos 5 minutos | menos de 1 minuto |

Entre las dos hay **tres órdenes de magnitud de diferencia en plata**, así que
son dos herramientas y dos ramas, no una con un «o esto o aquello» adentro. Un
pedido que trae `clips` y `foto` juntos se rechaza y se pregunta: adivinar ahí
es adivinar con la plata del cliente.

En la tabla `reels` se distinguen por la columna `clips`. Comparten estados, así
que las dos ramas se saltean explícitamente las filas de la otra — sin eso, el
camino de IA le pediría un video a un modelo por una fila que ya tiene el
material, y el montaje viejo reventaría buscando un `clip_url` inexistente.

### Los subtítulos salen con la tipografía de la marca

Una imagen por frase, dibujada con Chromium, que ffmpeg muestra en su ventana de
tiempo con `enable=between(t,…)`. **No es cuadro por cuadro, y es una decisión
de costo:** el rótulo sale barato porque se queda quieto (23 capturas de 90),
pero un subtítulo cambia durante todo el reel y esa optimización no aplica —un
reel de 60 s serían 1.800 capturas—. Doce frases son doce capturas.

Si algún día se quiere el subtítulo animado palabra por palabra, eso sí necesita
cuadro por cuadro, va en `rotulos.py`, y es otra decisión con otro costo.

El tamaño lo decide el mismo guardián que las placas (`render.QUE_ENTRE`): la
regla de 42 caracteres por línea que valida el guion es una cuenta de LETRAS,
que es exactamente lo que dejó salir «PAPANICOLAOU» cortado esta misma mañana.

**Todavía NO hay transcripción automática.** El agente escribe los subtítulos —
que para material corto ya elegido es lo natural, porque conoce el guion. Poner
las palabras de lo que se dice en el video necesita una API de reconocimiento de
voz, que es un costo nuevo por minuto y una decisión aparte.

### Tres cosas que salieron de probarlo, no de pensarlo

**El nombre del archivo bajado sale de la URL, no de un contador.** El guion
dice «clipA.mp4» porque ese es el nombre que la persona vio en el chat.
Bajándolos como `clip1.mp4`, el guion pedía un archivo que no existe y el reel
fallaba en la validación —con un mensaje correcto y desconcertante— sin que
nadie hubiera escrito nada mal. Pasó en la primera corrida.

**El velo se dibuja solo si la marca no lo tiene.** El degradado que hace
legible el texto es una entrada obligada de la cadena de ffmpeg, y una marca que
nunca hizo reels no tiene ese PNG. Stadium no lo tiene, y fue justo el caso de
la prueba: sin esto, el primer montaje de un cliente nuevo falla por un archivo.

**El CSS de la marca va ANTES que el del subtítulo.** Al revés, su
`.canvas{background:#FFFFFF}` pisaba el fondo transparente y el subtítulo salía
con un rectángulo blanco tapando el video. Es la misma trampa que ya estaba
anotada en `reelero.rotulo()` y volvió a aparecer en otro lado.

### Cómo se probó

| Prueba | Resultado |
|---|---|
| El camino entero del worker, marca real de Stadium | dos clips cortados y pegados, el segundo en cámara lenta, dos subtítulos quemados, audio mezclado: 1080×1920 a 30 fps y **9,98 s**, que es lo que da la cuenta |
| Una fila del camino viejo en la misma corrida | quedó intacta, las dos ramas no se pisan |
| Un subtítulo de 57 caracteres cuya primera palabra tiene 26 | se achica solo, se parte en tres líneas y entra |
| Los cinco rechazos de la puerta | `clips_y_foto`, `falta_el_guion`, `clip_invalido`, `demasiados_clips`, `falta_la_foto` |
| `deno check` de `api-reels` | limpio |

### Lo que hay que saber para el próximo

**El agente sólo sabe lo que le dicen.** El catálogo se genera de las
plantillas, así que todo lo que el motor sabe hacer y no es una plantilla es
invisible — por eso el agente de Clínica juraba que no podía hacer carruseles.
Por eso acá `montar_reel` es una herramienta propia con su descripción, y no un
parámetro más escondido adentro de `crear_reel`.

**`estado_reel` ahora distingue los dos casos.** Decía «el video lo genera una
IA y a veces deforma caras y manos» — cierto para `crear_reel` y **falso** para
un montaje con material real del club. La base devuelve `montado` y la
herramienta dice lo que corresponde a cada uno.

---

## Montaje de reels: darlo de alta en un cliente (31/8/2026)

Editar videos que el cliente ya tiene es la capacidad más ancha que construimos:
**toda empresa filma cosas y casi ninguna las edita.** No cuesta créditos, así
que no hay ninguna razón para tenerla en un cliente sí y en otro no.

### Lo primero: no confundirla con el motor de video

Son dos permisos distintos y estuvieron atados por error hasta hoy.

| | Generar video con IA | Montar material propio |
|---|---|---|
| Qué hace | un modelo INVENTA el video | corta y pega lo que ya existe |
| Cuesta | miles de créditos por pieza | **nada** |
| Necesita | bloque `reels` en `marca.json`, clave de Magnific, topes | sólo la tabla |
| Se pide con | `crear_reel` | `montar_reel` |

`atender()` chequeaba el bloque `reels` **antes** del montaje, así que una marca
sin el motor de video prendido —Clínica— no podía ni pegar dos clips suyos, que
es lo más barato que hace el sistema. El montaje ahora corre primero y con ficha
vacía. Una base sin tabla `reels` tampoco rompe: `_pendientes` ya devolvía vacío
ante un 404.

### Los cuatro pasos

**1 · La base.** Correr `migraciones/montaje-de-reels.sql` en el Supabase del
cliente. Es idempotente y sirve para los dos casos: crea la tabla si no está, y
si ya estaba le agrega `clips`, `guion` y vuelve `foto` opcional.

**2 · La Edge Function.** Desplegar `api-reels`. Es el mismo código para todos;
lo único propio del cliente son sus variables (`API_CLAVE`, `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`).

**3 · El worker.** Un solo despliegue sirve para todos los clientes: es la misma
imagen. Trae el motor, Whisper y el corte de tiempos muertos.

**4 · Las herramientas en Asistime.** Dos, con el mismo código que Boss (tenant
119, ids 2139 y 2132) cambiando la URL de la función y la `API_CLAVE`:

· `montar_reel` — la puerta. Su descripción tiene que decir con todas las letras
  que NO gasta créditos y que `crear_reel` sí: es la única forma de que el
  agente elija bien cuando la persona mandó videos.
· `estado_reel` — sirve para los dos caminos y los distingue por el campo
  `montado` que devuelve la función. Importa: sin eso le dice a la persona que
  «el video lo generó una IA y puede deformar caras», que en un montaje con
  material real es falso.

**5 · Asignárselas al AGENTE.** Este paso faltaba en la receta y costó una
prueba fallida el 31/8: crear la herramienta en el cliente NO la pone a
disposición de nadie. En Asistime las herramientas se crean a nivel cliente y
después se asocian a cada agente por separado. Con `montar_reel` creada pero sin
asignar, el Diseñador de Boss contestó —con toda coherencia— que no podía editar
videos: para él esa herramienta no existía.

Va por la interfaz: **Agentes → el agente diseñador → Herramientas → marcar la
nueva → Guardar.**

**No lo intentes por la API.** El único endpoint que hay
(`PUT /tenants/{id}/agents/{id}/tools`) REEMPLAZA la lista entera, y el `GET`
que la lee devuelve cada herramienta con su código completo, así que la
respuesta viene cortada y no se puede reconstruir qué tenía antes. Mandar una
lista incompleta le borra herramientas a un agente que funciona. El filtro
`?fields=id,name` se ignora.

### Lo que hay que decidir por cliente

**El vocabulario de la marca.** Sale de `NOMBRE` y de un `VOCABULARIO` opcional
en el `marca.py`, y se le pasa a Whisper como pista. No es cosmético: medido,
«Boss Padel» se transcribía «vos panel», y con la pista salió bien. Un cliente
sin vocabulario propio va a ver su nombre mal escrito en su propio reel.

**Nada más.** No hay modelo que elegir, ni tope de créditos, ni duración por
defecto: todo eso es del otro camino.

### Lo que conviene mirar antes de prometerlo

**El material.** Esto brilla con alguien hablando a cámara. Un peloteo de pádel
no tiene nada que subtitular y casi nada que recortar, así que en Boss el valor
está en pegar y encuadrar, no en los subtítulos.

**El audio de los clientes no sale a ningún lado.** Whisper corre adentro del
worker. Para Clínica Preventiva eso no es un detalle: es la diferencia entre
poder ofrecerlo y no poder.

---

## Cuánto tarda un reel, y por qué tardaba veinte minutos (31/8/2026)

El primer reel que pidió un cliente de verdad —Boss, tres videos de WhatsApp,
61,3 segundos de material— **se comió los 30 minutos de límite del job y murió
sin terminar**. La fila quedó en `montando` para siempre, sin error y sin
avisarle a nadie.

Esto es lo que estaba mal. Ninguna de las cuatro cosas era la máquina: las
cuatro estaban escritas en el código.

### 1 · `-preset slow -crf 18`

La peor, y la más fácil de no ver. Es calidad de masterizado —la que usarías
para un archivo que va a cine— aplicada a un video que Instagram vuelve a
comprimir a una fracción de ese bitrate apenas se sube. **Esa calidad no la ve
nadie**: se paga entera en tiempo de máquina y se tira en el camino.

Y no se pagaba una vez: `VIDEO_X264` se aplica **una vez por tramo**, y el
recorte de silencios convierte tres clips en diez tramos. Se pagaba diez veces.

Ahora es `veryfast` + `crf 20`. Después del recomprimido de Instagram el
archivo es indistinguible.

### 2 · El desenfoque del fondo, a resolución completa

`gblur=sigma=42` sobre 1080×1920, y para un 16:9 eso significaba primero
agrandar la fuente a 3413×1920 —tres veces el cuadro final— y desenfocar todo
eso, cuadro por cuadro. Era el filtro más caro del motor.

Y era gratis de arreglar, porque un desenfoque fuerte destruye justamente el
detalle que la resolución aporta: se achica a un sexto, se desenfoca ahí con un
sexto del radio, y se agranda de vuelta. Se ve igual, con 36 veces menos
píxeles que tocar.

### 3 · Dos recodificaciones enteras para pegar texto

Los subtítulos y el hook eran dos funciones y dos llamadas a ffmpeg, y **cada
una recodificaba el reel entero**. El hook —un cartel que se ve tres segundos—
costaba una pasada completa de codificación sobre el minuto de video.

Son la misma operación (pegar un PNG encima del cuadro durante un rato) y el
`filter_complex` encadena tantas capas como haga falta. Ahora es una sola
pasada, `_quemar_textos`.

De paso: esa pasada no decía con qué codificar, así que ffmpeg elegía solo
—`preset medium`, `crf 23`— y la última etapa que toca la imagen salía más
lenta **y** peor que los tramos. Ahora usa `VIDEO_X264` como todo lo demás.

### 4 · Un Chromium por subtítulo

`_subtitulo_png` abría un navegador, sacaba una foto y lo cerraba. Con 22
subtítulos eran 22 arranques de Chromium —perfil nuevo, GPU de mentira,
primera compilación de la hoja de estilo— para sacar 22 fotos de un texto
blanco. Ahora `_subtitulos_png` los dibuja todos en una sola pestaña.

Se aprovechó para cambiar el `wait_for_timeout(280)` por `document.fonts.ready`.
Un rato dormido es lo peor de los dos mundos: de más cuando la tipografía ya
estaba (el caso normal) y de menos el día que tarde, en el que `QUE_ENTRE`
mediría la tipografía de reemplazo y achicaría la frase contra un ancho que no
es el que se va a dibujar.

### 5 · Los tramos se comprimían con cuidado para tirarlos

Esta salió de medir, no de leer. Cuando el reel lleva subtítulos o hook, cada
tramo es un archivo **de paso**: se pega con los otros y esa unión se vuelve a
codificar entera para quemarle el texto encima. O sea que la compresión
cuidadosa de cada tramo se pagaba y se descartaba treinta segundos después.

`VIDEO_INTERMEDIO` (`ultrafast`, `crf 18`) invierte el trato para ese caso:
sale rápido, ocupa más —un rato, en `/tmp`— y llega al paso final sin haber
perdido nada que se note. La decisión la toma `reel()`, que es el único lugar
que sabe si viene una pasada más; si no viene ninguna, el tramo **es** el
resultado y se codifica con `VIDEO_X264` como siempre.

### La medición

Mismos tres clips reales de Boss, misma máquina de 4 núcleos, de punta a punta:
transcribir, cortar tiempos muertos, 10 tramos, 22 subtítulos, hook y mezcla.
Salen 55,3 segundos de reel.

| | Antes | Ahora |
|---|---|---|
| Tiempo total | **7 min 6 s** | **2 min 43 s** |
| Trabajo de máquina | ~1.224 s de CPU | ~490 s de CPU |
| Archivo | 27,5 MB | 39,6 MB |

**2,6 veces más rápido, con 2,5 veces menos trabajo de máquina.** El archivo
pesa más porque `veryfast` comprime menos que `slow` — y se ve igual o un poco
mejor, porque el bitrate más alto compensa de sobra en material de cámara en
mano. 40 MB para un reel de un minuto no es problema para Instagram.

El job además pasó de **2 núcleos a 8**, así que en producción el tiempo real
va a ser bastante menor que esos 2 min 43 s.

### Dónde queda el tiempo ahora

Cronometrado etapa por etapa, sobre el mismo reel:

| Etapa | Segundos | % |
|---|---:|---:|
| Codificar los tramos | 89,3 | 55 % |
| Quemar subtítulos y hook | 41,5 | 26 % |
| Transcribir (Whisper) | 23,3 | 14 % |
| Mezclar el audio | 5,4 | 3 % |
| Dibujar los subtítulos (Chromium) | 5,3 | 3 % |
| Dibujar el hook (Chromium) | 1,1 | 1 % |

Los 22 Chromium que antes eran minutos ahora son 5 segundos: ese frente está
cerrado.

**Lo que queda es codificar, y no hay mucho más para sacar sin romper algo.**
Se midió aparte la cadena de filtros de un tramo, y de los 24,8 s que tarda,
**13,6 son del `unsharp`** — más que la mitad. Se probó bajarlo a un núcleo de
3×3 (ahorra 2,3 s: el costo no es el tamaño del núcleo) y reemplazarlo por
`cas`, que se supone el sharpener más moderno y **tardó 38 s, mucho peor**. Así
que el `unsharp` se queda: es caro y está comprando algo real — estos clips
vienen en 464×832 y se agrandan 2,3 veces, que es exactamente el caso para el
que está puesto.

El golpe de zoom, que parecía el sospechoso obvio por rescalar cuadro a cuadro,
cuesta **0,5 s**. No tocarlo.

El job además pasó de **2 núcleos a 8** en `desplegar-chat.sh`. Cloud Run cobra
por núcleo-segundo, no por corrida: cuatro veces la máquina durante un tercio
del tiempo sale aproximadamente lo mismo por reel. La cuenta no da exactamente
igual —x264 no escala perfecto— pero la diferencia de precio es de centavos y
la de espera es de minutos.

### Lo que queda por hacer, y no se puede desde este repo

**El modelo de Whisper se baja en cada corrida, y con `medium` eso ya no es
un detalle de velocidad: es lo que rompe el job.** El contenedor es efímero,
así que el modelo viaja de HuggingFace cada vez. Con `small` eran 464 MB y
~9 segundos, molesto y nada más. Con `medium` son 1,5 GB — y en Cloud Run
**el disco del contenedor es memoria**, así que esos 1,5 GB salen del límite
del job antes de que empiece a trabajar.

Se arregla en el `Dockerfile`, que **no está en este repo** —vive sólo en el
worker, en `~/worker/Dockerfile`—. **No lo pegues a mano:**

```bash
python3 ~/worker/herramientas/hornear-modelo.py
```

Lo agrega en el lugar correcto, deja una copia de seguridad y es idempotente.
Esto es un comando y no una instrucción por una razón: la instrucción estuvo
escrita acá desde el principio y **nunca se siguió**. El modelo se venía
bajando en cada corrida desde siempre, sin que nadie lo notara, porque con
`small` sólo costaba unos segundos. Una instrucción que hay que acordarse de
seguir no es una instrucción, es una apuesta.

Esto es lo que agrega:

```dockerfile
# Precarga el modelo de transcripción: el contenedor es efímero y sin esto el
# modelo se baja de HuggingFace en CADA corrida. Con `medium` son 1,5 GB, y en
# Cloud Run el disco del contenedor es memoria: sin esta línea el job se queda
# sin memoria en vez de tardar un poco más.
ENV HF_HOME=/opt/modelos
RUN python -c "from faster_whisper import WhisperModel; \
      WhisperModel('medium', device='cpu', compute_type='int8')" \
    && chmod -R a+rX /opt/modelos
```

El `HF_HOME` explícito no es adorno: sin él la caché queda en el `$HOME` del
usuario que corrió el `RUN`, y si el job corre con otro usuario no la puede
leer — se baja igual y no se entera nadie.

**Si el modelo tuvo que bajarse, el worker ahora lo dice.** `habla._cargar()`
mide cuánto tardó y, si pasa de 20 segundos, escribe un `warning` diciendo que
casi seguro no está horneado. Un aviso no arregla nada, pero convierte «el reel
se colgó» en «se está bajando el modelo», que es la diferencia entre media hora
de búsqueda y treinta segundos.

---

## Un montaje que se muere tiene que decir que se murió (31/8/2026)

El job se corta solo a los 30 minutos (`--task-timeout 30m`). Cuando eso pasa
el proceso desaparece de golpe: no corre ningún `except`, no se escribe ningún
error, y **la fila queda en `montando` para siempre**. Sin URL, sin motivo, y
sin que nadie la vuelva a mirar, porque el bucle de montajes sólo levanta filas
en `pendiente`.

Le pasó al primer reel de verdad y no se enteró nadie hasta que fuimos a mirar
la base a mano. Es la diferencia entre «perdón, falló, mandámelo de nuevo» y un
cliente esperando un video que no va a llegar nunca.

`_rescatar_montajes` corre ahora al principio de `atender_montajes`: busca
montajes quietos en `montando` hace más de **35 minutos** y los pasa a `error`
con un texto en castellano que el agente puede leerle al cliente.

Los 35 minutos son a propósito más que el límite del job: **mientras el proceso
todavía pueda estar vivo, la fila es suya y no se toca.** Y el cambio de estado
va con el mismo `_tomar` con filtro por el estado viejo que usa el resto: si
entre la consulta y el PATCH el proceso terminó y puso `listo`, este PATCH no
toca nada, en vez de pisar un reel que salió bien con un error que no ocurrió.

---

## El reel salía al revés (31/8/2026)

El primer montaje que terminó bien contó la historia de atrás para adelante:
abría con la respuesta y cerraba con la pregunta. Técnicamente impecable —hook,
subtítulos, tiempos muertos, todo bien— y completamente inservible.

Los tres videos llegaron así:

```
15.36.24  ·  15.36.15  ·  15.35.59
```

El más nuevo primero, que es como los lista la bandeja. El motor los pegaba «en
el orden en que llegaron», una regla que suena neutral y no lo es: **nadie
quiere nunca sus clips al revés.**

El agente no puede arreglarlo — ve URLs, no relojes. El worker sí tiene los
nombres, y los nombres traen la hora. `_en_orden` los ordena por ahí.

Tres frenos, para que no invente un orden que no le consta:

1. **Sólo reordena si TODOS los clips dicen cuándo se grabaron.** Si uno no lo
   dice, se respeta entero el orden que vino: mezclar los que tienen hora con
   los que no daría un orden peor que cualquiera de los dos, y sin manera de
   explicarlo.
2. **Sólo si todas las horas son distintas.** Con dos iguales no hay orden que
   afirmar.
3. **No toca nada si el guion trae `tramos`.** Ahí alguien ya miró el material
   y dijo qué va primero; esto es el default para cuando nadie lo dijo.

Y cuando reordena **lo dice** en las `notas` de la fila, así el agente se lo
puede contar a la persona en vez de que parezca magia.

Entiende `WhatsApp Video 2026-08-31 at 15.36.24.mp4`, `VID_20260831_153624.mp4`
y `20260831_153624.mp4`, que es lo que manda la gente de verdad. Un número
largo que no sea una fecha válida (`20261345`) no cuenta como fecha.

---

## Corregir un reel sin rehacerlo (1/9/2026)

Había una asimetría al revés de como tenía que estar: **acertar era caro y
corregir era todavía más caro.**

Armar un reel con subtítulos automáticos cuesta escuchar el audio entero,
partirlo en frases, medir los silencios y escribir un hook. Cuando de 22 frases
salían 2 mal transcritas, lo único que hacía falta era cambiar dos textos. Pero
el motor tiraba lo que había resuelto, así que la única salida era rehacerlo
entero: volver a escuchar —y **equivocarse exactamente igual**, porque el modelo
es determinista con el mismo audio— y de paso tirar las 20 que estaban bien.

### Las tres piezas

**1 · El motor guarda lo que armó** (`armado`, ver `motor.video.desde_guion`).
No es un formato nuevo: es un guion válido, el mismo que entra por arriba, con
lo automático ya decidido. Devolvérselo lo redibuja igual.

Se le sacan `cortar_silencios` y `duracion_objetivo`. **No es un detalle**: si
quedaran, cada retoque volvería a recortar tramos ya recortados y a elegir
dentro de una selección ya hecha. El reel se iría comiendo solo un poco en cada
corrección hasta quedar en nada.

**2 · El retoque** (`motor/retoque.py`). Lo que aporta no son los cambios de
texto —eso es un `replace`— sino los de estructura:

> **Sacar un tramo no es sacar un tramo.** Los subtítulos viven en el reloj del
> reel. Si se saca el tercero de diez, todo lo que venía después se adelanta y
> las frases empiezan a aparecer tarde, cada vez más desfasadas hasta el final.
> El reel sale PEOR que antes de corregirlo y nadie entiende por qué. Así que
> al tocar la estructura, cada frase se ata al tramo donde suena y viaja con
> él; las que sonaban en lo que se sacó se van con él.

El orden de aplicación tampoco es el que venga: reemplazos globales, después
frases por número (lo específico pisa lo general), después hook y cierre, y la
estructura sola al final, que es la única que mueve los tiempos.

Un cambio imposible falla **en el segundo cero**, en castellano —«no existe la
frase 99: este reel tiene 22»— y no a los dos minutos con un video mal hecho.

Y el retoque **no pisa el original**: crea una fila nueva que lo apunta con
`origen`. Una corrección que salió peor no tiene que llevarse puesto lo que ya
estaba bien.

**3 · La marca aprende** (tabla `correcciones`). Un reemplazo casi siempre es un
nombre propio que la transcripción entiende mal, y lo entiende mal SIEMPRE
igual: «Boss Padel» sale «vos panel» en este reel y en todos los que vengan.

Lo aprendido se usa **de dos maneras, y las dos hacen falta**:

- **Antes de escuchar**, como vocabulario para el modelo. Eso *evita* el error.
- **Después de escribir**, como reemplazo sobre el texto. Eso lo *tapa*, y hace
  falta igual: el vocabulario ayuda pero no garantiza nada, y quien corrigió
  «vos panel» una vez tiene derecho a no volver a verlo nunca.

`recordar: false` es para el caso contrario: reescribir una frase para que suene
mejor en ESTE reel no es cómo se escribe esa palabra siempre. Y se puede
olvidar (`{"olvidar": "vos panel"}`), porque una memoria que no se puede
deshacer ensucia todos los reels que vengan sin que nadie sepa por qué.

### La API

| Qué | Cómo |
|---|---|
| Ver lo que armó | `GET ?id=<reel>&ver=1` — frases y tramos numerados **desde 1** |
| Corregir | `POST {"retocar":"<reel>","cambios":{…}}` |
| Ver la memoria | `GET ?correcciones=1` |
| Olvidar | `POST {"olvidar":"vos panel"}` |

Los `cambios` que entiende:

```json
{
  "reemplazar":  [{"de": "vos panel", "a": "Boss Padel"}],
  "subtitulos":  [{"n": 4, "texto": "la frase corregida"}],
  "hook":        "otro hook",
  "cierre":      "",
  "quitar":      [3],
  "orden":       [2, 1, 3],
  "recordar":    false
}
```

Una frase con `texto` vacío se saca. `cierre` vacío saca la placa final.

Los números van **desde 1** porque los va a decir una persona en un chat: nadie
cuenta desde cero fuera de la programación.

### Cómo se prende en un cliente

1. **`migraciones/retoque-de-reels.sql`** en el SQL Editor de ese cliente. Agrega `armado`, `origen` y la
   tabla `correcciones`. Es idempotente.
2. **Desplegar el worker** (`./desplegar-chat.sh`) y **la Edge Function**
   `api-reels`, que es donde viven `?ver=1`, `retocar` y la memoria.
3. **Crear las tools** con el código de `tools-asistime/` — cambiándoles la
   URL y la `API_CLAVE` por las de ESE cliente.
4. **Marcarlas en el agente**, en Agentes → Herramientas. Este paso va a mano:
   `PUT /agents/{id}/tools` reemplaza la lista entera y el `GET` que la leería
   viene cortado, así que mandarlo a ciegas le sacaría al agente herramientas
   que hoy funcionan.
5. **Agregarle al prompt del agente** la sección «Corregir un reel que ya
   salió», la fila en la tabla de puertas y la línea de «no rehagas un reel para
   corregirle una frase». Sin eso las tools existen y el agente no las llama —
   es exactamente lo que pasó con `montar_reel` el 31/8.

### Cómo quedó en los tres clientes (1/9/2026)

Los pasos 1, 2, 3 y 5 están hechos en los tres. **Falta el paso 4 en los tres**,
que es el del panel:

| | Boss (119 / ag. 364) | Stadium (176 / ag. 544) | Clínica (73 / ag. 542) |
|---|---|---|---|
| migración | ✅ | ✅ | ✅ |
| `api-reels` | ✅ | ✅ v5 | ✅ v1, nueva |
| `montar_reel` | ya estaba | 2149 | 2153 |
| `ver_reel` | 2143 | 2150 | 2154 |
| `retocar_reel` | 2144 | 2151 | 2155 |
| `estado_reel` | ya estaba | 2076 | 2152 |
| prompt | v15 | v4 (4775) | v6 (4776) |
| **tildar en el panel** | ❌ | ❌ | ❌ |

Dos cosas que no son iguales en los tres:

- **Stadium tiene las dos formas de hacer un reel** y una sola `estado_reel` que
  contesta por las dos. Se ramifica con el `montado` de la API; el porqué está
  en `tools-asistime/LEEME.md`.
- **Clínica no puede publicar video.** Sus tools de publicación suben fotos y
  piezas, no reels. El prompt lo dice con todas las letras y le prohíbe
  prometerlo: el reel se entrega como link y lo suben ellos.

**Los reels hechos antes de esto no se pueden retocar** — no tienen `armado`
guardado. La API lo dice con esas palabras en vez de fallar raro: «se armó antes
de que el motor guardara su guion; pedilo de nuevo y el nuevo sí».

---

## La transcripción inventaba frases (1/9/2026)

Joaquín marcó que los subtítulos «erran en cosas muy básicas». Tenía razón, y
medido contra el material real era peor de lo que parecía.

Tres clips de Boss, lo que se dice contra lo que escribió el motor:

| se dice | `small` (lo que había) |
|---|---|
| teletransportarme | «Te le transportarme» |
| ¿para ir hacia dónde? | «¿Pareita sea donde?» |
| poder volar | «por volar» |
| el campeón del siglo | «El Campeón de Silo» |
| ¿cuál elegirías? | «cuáles digirías» |
| para revivir lo del campeón del siglo | «Para reivir los campeones del siglo» |
| *(nadie lo dijo)* | **«futbol es un superpoder»** |

La última fila es de otra categoría. No entendió mal: **inventó una frase que
nadie dijo** y la puso de subtítulo en un video de un cliente.

### Tres cosas, medidas

**1 · El modelo.** Con `medium`, sobre los mismos tres clips, no queda ni un
error. `large-v3` devuelve exactamente el mismo texto —una interjección más—
por casi el doble de tiempo y el doble de peso: no se paga.

| | error | transcribir (4 núcleos) | modelo |
|---|---|---|---|
| `small` int8 | 6 errores + 1 frase inventada | 20 s | 464 MB |
| **`medium` int8** | **ninguno** | **45 s** | 1,5 GB |
| `large-v3` int8 | ninguno | 80 s | 2,9 GB |

El comentario que había en `habla.py` decía que `medium` «no se nota en frases
cortas». Era falso. Lo que había cambiado no era el modelo sino el
presupuesto: `small` se eligió cuando un reel tardaba siete minutos y cada
segundo contaba; hoy tarda minuto y medio, y el worker corre en ocho núcleos.

**2 · El vocabulario iba como lista, y eso empeoraba la puntuación.**
`initial_prompt` no es una lista de palabras clave: es «el texto que venía
justo antes», y el modelo **copia su estilo, puntuación incluida**. Con
`"Boss Padel, pádel, Carrasco, …"` empezó a escribir «cual elegirías?», «Para
ir a donde?» — sin abrir los signos. Le estábamos enseñando, sin querer, que
en este texto no se abren interrogaciones.

Escrito como una frase normal con sus signos, la puntuación sale perfecta:

```
Hablamos de pádel en Boss Padel, con canchas en Carrasco, Hípico y
Punta del Este. ¿Jugamos un americano? Buena pala, lindo revés.
```

Por eso `VOCABULARIO` en `marca.py` es una frase y no una tupla, y por eso las
correcciones aprendidas se pegan con `habla.en_frase()` en vez de con comas.

**3 · Ninguna marca tenía vocabulario.** El motor estaba preparado para que
cada cliente listara sus nombres propios y no lo usaba nadie: los tres
`marca.py` no definían `VOCABULARIO`, así que al modelo le llegaba sólo el
nombre de la marca. Ahora los tres lo tienen. En Clínica es donde más rinde
—psicotécnico, espirometría, Papanicolaou se repiten en cada video—.

### Lo que NO se hizo, y por qué

**No se prendió el VAD.** Filtrar el audio por detección de voz mejora a
`small`, pero recorta lo que juzga silencio — y la transcripción es
justamente lo que le prohíbe al recorte comerse una palabra (ver el caso de
Bruno, más abajo). Un VAD que se traga media frase reabre ese agujero desde
el otro lado. Con `medium` no hace falta.

### Se tuvo que volver atrás el mismo día, y después volver a entrar bien

Se desplegó con `medium` y **un reel que tardaba 1 m 23 s pasó de largo los
ocho minutos** — el mismo pedido, los mismos tres clips. Se volvió a `small`.

La medición de calidad era correcta; lo que no se midió es si el worker podía
pagar ese modelo. **En Cloud Run el disco del contenedor es memoria.** Bajar
`medium` consume 1,5 GiB de los 4 GiB del job, cargarlo consume otro tanto, y
al lado hay un Chromium dibujando subtítulos y un ffmpeg trabajando sobre
cuadros de 1080×1920. No es que tarde más: es que no entra.

Medir la calidad de un modelo en una máquina con 26 GB libres y deducir que
entra en un contenedor de 4 GiB es exactamente el error que este archivo
existe para no repetir. **Un modelo no se elige por su calidad sino por su
calidad dentro del presupuesto que hay.**

### La cuenta que faltaba, ahora medida

| | pico de memoria | transcribir (4 núcleos) | modelo en disco |
|---|---|---|---|
| `small` | 781 MiB | 34 s | 464 MB |
| `medium` | **2.102 MiB** | 78 s | 1,5 GB |

Con el modelo sin hornear hay que sumarle los 1,5 GiB que ocupa bajarlo:
**3,6 GiB de los 4 GiB que tenía el job**, con un Chromium y un ffmpeg todavía
por arrancar. Ahí murió.

### Las tres cosas que van juntas

`medium` no se prende solo. Va con las dos sin las cuales no se sostiene:

1. **El modelo horneado en el `Dockerfile`** (la línea está más arriba en este
   mismo archivo, ya apuntando a `medium`). Sin esto se baja 1,5 GB en cada
   reel.
2. **El job en 8 GiB**, ya puesto en `desplegar-chat.sh`. 2,1 GiB de pico más
   Chromium más ffmpeg entra en 4 GiB por poco, y «por poco» es como se
   llegó acá.
3. **`WHISPER_MODELO` fijado en `desplegar-chat.sh`**, no en el código:
   `--set-env-vars` reemplaza la lista entera, así que una variable puesta a
   mano con `--update-env-vars` sobrevive hasta el próximo despliegue y
   después desaparece sin que nadie lo note.

Y si algo sale mal se vuelve sin tocar código:
`WHISPER_MODELO=small ./desplegar-chat.sh`.

### Lo que se aprendió, que vale más que el modelo

Medir la calidad de un modelo en una máquina con 26 GB libres y deducir que
entra en un contenedor de 4 GiB fue el error. **Un modelo no se elige por su
calidad: se elige por su calidad dentro del presupuesto que hay**, y el
presupuesto se mide igual que la calidad. Los 2.102 MiB de la tabla de arriba
son treinta segundos de trabajo que habrían evitado un despliegue roto.

---

## «A mídia não está pronta para ser publicada» (1/9/2026)

Se pidió publicar una placa de Clínica y volvió ese error, en portugués. La
pieza estaba bien, la cuenta estaba bien, el pie de foto estaba escrito. Meta
todavía estaba terminando de procesarla, y nada más.

Fila `63f9c45a` de `publicaciones`: `estado = error`, `intentos = 1`,
`esperas = 0`. Los tres números cuentan la historia.

### Eran dos errores encimados

**Uno: no se le preguntaba a Meta si la pieza estaba lista.** Al crear un
contenedor, Meta lo procesa antes de dejarlo publicar, y se pregunta con
`status_code` hasta que diga `FINISHED`. El worker sólo lo preguntaba para
videos. Una foto se publicaba derecho —está lista al instante— que es verdad
tantas veces seguidas que parecía una regla en vez de una probabilidad.

**Dos: cuando Meta avisó, se tomó como definitivo.** El código 9007 no estaba
en `CODIGOS_TEMPORALES`, así que el posteo fue a `error`, que es el estado del
que no se vuelve. El mensaje decía textualmente «aguarde um momento» y se lo
dio por perdido: con reintentar a los cinco minutos alcanzaba.

El primero es la causa. El segundo es lo que convirtió una demora de un segundo
en un posteo perdido, y es el que más importa: sin él, esto habría sido un
reintento que nadie miraba.

### Los dos arreglos

1. **Se espera a todo contenedor, no sólo a los videos.** `ESPERA_FOTO` son 20
   segundos —una foto contesta `FINISHED` en la primera pregunta casi siempre—
   contra los 90 de un video. Si no llegó, la fila queda en `subiendo` con su
   contenedor guardado y la corrida siguiente la retoma, igual que los videos.
2. **9007 es temporal**, y su texto se traduce: «Instagram todavía estaba
   terminando de procesar la pieza. Se reintenta solo en unos minutos.» Meta
   contesta en el idioma de la app, y un error en portugués no le dice nada a
   nadie.

Lo segundo hace falta igual que lo primero: entre preguntar y publicar hay una
carrera que ninguna espera cierra.

### El guardián

```bash
python3 herramientas/probar-publicacion.py
```

No toca Instagram ni la base. Fija las tres cosas: que la foto se espere, que
un «esperá un momento» se reintente, y que **un rechazo de verdad se siga
informando como error** —sin lo tercero, la prueba pasaría con un publicador
que reintenta todo para siempre y nunca avisa nada.

En Cloud Shell hace falta `pip3 install --quiet pillow requests` una vez:
`publicador` importa Pillow arriba de todo y esa máquina no lo tiene. Si falta,
la prueba lo dice y sale bien en vez de tirar un `ModuleNotFoundError` que
parece que el worker está roto — igual que `probar-recorte.py` con ffmpeg.

**El Instagram de mentira rechaza publicar un contenedor que no está listo, y
eso es lo que hace que la prueba sirva.** La primera versión dejaba publicar
siempre, así que pasaba también contra el código roto. Un doble más amable que
el original convierte la prueba en un adorno — el mismo error que la primera
versión de `probar-recorte.py`.

---

## El recorte se comió la respuesta (31/8/2026)

Salió un reel donde alguien le pregunta a Bruno qué superpoder elegiría **y la
respuesta no está**. Quedó la pregunta hecha, un remate colgando y ningún
sentido. Desaparecieron 6,4 segundos con nueve palabras adentro.

### La causa no era la que parecía

La primera lectura fue que la respuesta se había dicho más lejos del micrófono
y la energía no la había oído. **Falso, y conviene que quede escrito porque era
una explicación creíble:** medida, la respuesta se oye a −28 dB, igual de fuerte
que todo lo demás.

Lo que pasó es más sutil. Bruno contesta a las corridas —pregunta, respuesta,
repregunta— con pausas cortas en el medio, así que el clip quedó partido en
**cinco islas de habla de unos 0,75 s cada una**. Y `min_tramo` valía 0,8.

Ninguna isla llegaba al mínimo, así que se descartaron **las cinco**, una por
una. Cada descarte era defendible por separado; el conjunto fue un desastre.

`min_tramo` está para tirar basura —medio segundo de audio suelto entre dos
silencios casi nunca es una palabra, es un ruido, y como tramo de video es un
parpadeo—. El error fue no darle la excepción obvia: **si adentro hay una
palabra, no es basura.** Un parpadeo es un problema estético; perder lo que
alguien dijo es de otra categoría.

### Los dos arreglos

1. **`min_tramo` no descarta un tramo que contenga una palabra.** Es el arreglo
   del caso de Bruno.
2. **La transcripción vetea los silencios.** Antes las palabras servían para
   AGREGAR cortes y para que un corte no partiera una palabra al medio, pero
   nada impedía que un corte se tragara palabras **enteras**: si ninguna caía
   justo sobre el borde, los dos bordes parecían limpios. Ahora se le resta a
   los silencios todo lo que sea habla. La energía propone dónde cortar; la
   transcripción tiene la última palabra sobre dónde **no**.

### El guardián

```bash
python3 herramientas/probar-recorte.py
```

Arma un audio de laboratorio con ffmpeg y comprueba las dos mitades del
contrato, que tiran para lados opuestos: **que no se pierda ninguna palabra** y
**que el silencio de verdad se siga yendo** —sin lo segundo, la prueba pasaría
con un recorte que no recorta.

**El libreto son ráfagas cortas y no bloques largos, y eso importa.** La primera
versión de esta prueba usaba dos segundos seguidos de habla floja y **pasaba
también con el código roto**: no reproducía nada. Un test que no falla contra el
bug que dice cubrir es peor que no tener test, porque da permiso para no mirar.

Medido después del arreglo, sobre el material real de Bruno: 33,6 s → 30,2 s, y
**cero palabras perdidas** en los tres clips.

### Lo que cuesta

Se recorta menos: donde antes decía «saqué 9,2 s» ahora saca 3,4 s. **Ese número
viejo era mentira**: 6,4 de esos 9,2 eran diálogo, no tiempo muerto. Un reel
sale un poco más largo y entero, que es el único orden aceptable de esas dos
cosas.

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
