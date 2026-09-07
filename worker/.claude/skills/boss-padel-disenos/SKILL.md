---
name: boss-padel-disenos
description: Genera piezas de diseño para redes sociales de Boss Padel (el club de pádel más grande de Uruguay — sedes Carrasco, Hípico y Punta del Este) con la identidad real de la marca — logo BOSS PADEL 0000, negro #0A0A0A, lima #E4FF02, naranja #ED7F3E, azul #1C5D7D, tipografías Archivo + Barlow, los 4 aros y el salpicón orgánico. Incluye 14 plantillas listas (torneo, resultados, titular+foto, tipográfica, promo, agenda, countdown, campeones, tip, americano, socio, duelo, horarios, destacada) en 4 formatos (1080×1080, 1080×1350, 1080×1920). Usar SIEMPRE que Joaquín o el equipo pidan "una placa / arte / post / flyer / diseño para Boss Padel", "la placa del torneo", "el podio del torneo", "algo para el Instagram de Boss", "una story de Boss", "adaptá esta foto a la marca de Boss", o cuando mencionen @boss.padel, bosspadel.uy, o las sedes Carrasco / Hípico / Punta del Este en contexto de diseño o contenido. También cuando digan "otra opción", "hacelo en story", "cambiá la fecha / el teléfono / las categorías" sobre una pieza de este club, cuando pidan "una presentación / propuesta / dossier en PDF para un sponsor o una marca" del club, cuando pidan un efecto de clima ("que llueva", "como una ventana con gotas", "con niebla"), cuando suban una foto propia para usar en el diseño, o cuando pidan "un reel / un video / una cuenta regresiva en video" con fotos y clips del club. También cuando pidan "el americano del jueves", "la partida abierta", "el social", "el jugador o la jugadora de la semana", "el socio del mes", "una encuesta", "una pregunta para los comentarios", "un versus", o "las portadas de las historias destacadas". También cuando pidan "los horarios libres", "las canchas disponibles", "qué queda libre mañana", "la disponibilidad del sábado" o pasen una lista de horas con precios.
---

# Diseños Boss Padel

Sistema de diseño del club. Todo se renderiza con Chromium a través de `render.py`, así que la tipografía y el espaciado salen exactos.

## El camino corto

Una placa son cuatro pasos y ninguno más:

1. leer `referencias/fotos.json`, elegir foto y **copiar su `foco`**
2. escribir un `spec.json` con un trabajo por cada formato pedido
3. `python3 render.py spec.json <carpeta-de-salida>`
4. escribir `copy.txt` (sólo el texto del posteo) y `notas.txt`

Un carrusel o una secuencia de stories son un solo trabajo del mismo
`spec.json` — ver «Carruseles y secuencias» más abajo.

### `copy.txt` y `notas.txt` son dos archivos distintos

**`copy.txt` sale publicado tal cual en el Instagram del club.** Va sólo el
texto del posteo: nada de encabezados, ni «COPY PARA INSTAGRAM», ni
explicaciones, ni el pedido que te hicieron, ni separadores de guiones.

**`notas.txt` no sale de acá.** Ahí van las decisiones que tomaste, lo que
asumiste, lo que faltaba, lo que propondrías para la próxima.

El 9/8/2026 las dos cosas estaban en el mismo archivo y las ocho notas de
trabajo del diseñador —«asumí que hasta las 19:30 hay disponibilidad», «no puse
los nombres de las canchas»— terminaron públicas en la cuenta del club, abajo
de la pieza. La prueba para saber dónde va algo es simple: **¿lo leería un
socio del club sin entender de qué estás hablando?** Entonces va en
`notas.txt`.

**No explores la carpeta ni leas los `.py`** salvo que algo falle de verdad.
Todo lo que hace falta está acá abajo. Cada archivo que abrís se vuelve a leer
entero en cada turno que sigue, y de ahí sale el grueso del costo: en una placa
medida, generar la pieza fueron 21 centavos y releer contexto 78.

Y sobre todo **no entres a `motor/`**. Ahí está el código compartido con las
demás marcas —Chromium, ffmpeg, sonido, efectos, la estructura del carrusel— y
no hay nada que ajustar por pieza. Lo de Boss Padel es lo que está en esta
carpeta: `templates.py`, `brand.py`, `diapositivas.py` y `referencias/`.

## Lo esencial de la marca

Está completo en `referencias/marca.md`, pero para una placa normal alcanza con esto:

| | |
|---|---|
| Fondo | negro `#0A0A0A` — **nunca blanco** |
| Texto | blanco `#FAFAFA` |
| Acentos | lima `#E4FF02` · naranja `#ED7F3E` · azul `#1C5D7D` (fondos de promo) |
| Display | Archivo 300 Light + 700 Bold, interlineado 0.90 |
| Cuerpo | Barlow 300–900 · kickers Barlow Condensed 500, tracking 0.30–0.56em |
| Logo | `BOSS` en outline, nunca relleno. 180–230 px en pieza de 1080 |

Un solo acento por pieza. La única combinación doble permitida es texto lima +
salpicón naranja. Toda foto con texto encima lleva scrim.

## Antes de diseñar

1. **El teléfono NO va por defecto.** Los campos `contacto` de las plantillas
   quedan vacíos salvo que el pedido pida los datos de contacto, o que la pieza
   sea una convocatoria con inscripción donde el número es el punto. Una placa
   con un teléfono que nadie pidió se lee como publicidad barata. Agregarlo
   después es un pedido de treinta segundos; sacarlo obliga a rehacer la pieza.
2. **No preguntes: decidí.** El pedido llega por un formulario y no hay nadie
   del otro lado esperando para contestar. Si falta un dato, resolvelo con lo
   más razonable y dejá escrito qué asumiste en `notas.txt`.
3. **Elegí acento por sede:** Carrasco → `lima`, Hípico → `naranja`, Punta del Este → `lima`.
4. **Foto:** usá la que pase el usuario (copiala a `assets/`). Si no hay, elegí
   del banco leyendo `referencias/fotos.json`, que describe qué se ve en cada una
   y para qué sirve.
5. **Quién aparece:** si el pedido dice algo sobre las personas de la foto
   ("con jugadoras", "que se vea gente", "sin nadie", "un grupo"), filtrá por
   el campo `quien` de `fotos.json` antes de elegir. Si el banco no lo tiene,
   elegí lo más cercano y **decilo explícitamente** en la entrega, nombrando
   qué foto haría falta sumar. Callarlo es peor que no cumplirlo: el club no
   se entera de que le falta material. `_faltantes` en `fotos.json` lleva la
   lista de huecos al día. **Dos intentos de búsqueda y listo:** si ninguna foto
   cumple, agarrá la más cercana y seguí. Una pieza entregada con la foto que no
   era sirve; una que nunca se generó porque seguiste buscando, no.

   Para categoría femenina el banco tiene material propio y bueno: usalo.
   `jugadora-resto-azul` y `jugadora-resto-negro` son las placas insignia,
   `jugadora-saque` y `jugadora-golpe` las de acción, `jugadoras-dupla` la de
   campeonas, y `jugadora-cancha` la que deja más lugar libre para el titular.
   No anuncies un torneo femenino con una foto de un jugador hombre.
7. **Encuadre:** NO lo improvises. `referencias/fotos.json` trae el `foco` ya
   resuelto para cada foto y cada formato. Copialo tal cual al campo `foco`.
   Está fijo a propósito: si lo decidís de nuevo en cada corrida, la misma foto
   sale distinta cada vez y a veces la cara del sujeto choca con el titular.

## Cómo generar una pieza

Escribí **un solo** `spec.json` con todos los trabajos y corré una sola vez:

```bash
python3 render.py spec.json /ruta/de/salida    # los archivos salen ahí
python3 render.py spec.json                    # sin ruta, salen en out/
```

Un `spec.json` acepta cuantos trabajos quieras, así que post y story se
resuelven en la misma corrida: no hagas dos specs ni dos llamadas.

Cada trabajo tiene esta forma:

```json
{"plantilla": "torneo", "formato": "post", "nombre": "torneo-ago-post", "data": { ... }}
```

- `formato`: `post` (1080×1080) · `vert` (1080×1350) · `story` (1080×1920) · `reel` (1080×1920)
- Por defecto entregá **post + story**. Si piden más formatos, agregá trabajos con el mismo `data`.
- Para una presentación en PDF no se usa `formato`: ver «Presentaciones en PDF» más abajo.

## Antes de elegir el formato: leé esto

Tres reglas que salieron de medir, no de opinar. Metricool comparó 24.364.803
posteos entre 2025 y 2026:

**1 · Ante la duda, no es una placa: es un carrusel.**
La placa suelta perdió **45,98% de engagement** en un año. El carrusel da
**9 veces** más guardados y el reel **4 veces** más interacciones. La placa
suelta queda para el aviso puro —feriado, horario, cancha cerrada— donde no
importa el alcance. Si el contenido da para más de una idea, hacé el carrusel
aunque el pedido diga «una placa», y explicá por qué en `notas.txt`.

**2 · Sin hashtags en el caption.**
Los posteos con al menos un hashtag tuvieron **31,70% menos vistas**. En
Instagram restan. (En TikTok es al revés, pero acá no publicamos en TikTok.)

**3 · Todo caption cierra con una pregunta o un pedido de comentario.**
Una pregunta da **+36,70%** de comentarios; pedir el comentario da
**+202,78%**. Es gratis y es lo que más mueve la aguja de todo este documento.

Y una cuarta que no es de datos sino de oficio: **la primera diapositiva de un
carrusel es un gancho, no un título.** «TIPOS DE JUGADORES EN UN TORNEO BOSS»
es un gancho. «CARRUSEL DE AGOSTO» no.

## Las 14 plantillas

### `torneo` — la placa insignia
```json
{"fecha_l1":"28, 29 Y 30 DE","fecha_l2":"AGOSTO","sede":"CARRASCO",
 "cats_libres":"2DA, 3RA, 4TA, 5TA, 6TA","cats_fem":"3RA, 4TA, 5TA",
 "contacto":"097 406 148","foto":"assets/ph-cancha.jpg",
 "acento":"lima","blob_color":"naranja","cta":"INSCRIPCIONES<br>ABIERTAS"}
```
`fecha_l2` va con tracking más abierto que `fecha_l1` — es la firma tipográfica del club. El salpicón naranja siempre en la esquina superior derecha, detrás del logo.

### `resultados` — podio post-torneo
```json
{"titulo":"ASÍ QUEDÓ EL TORNEO","sede":"BOSS CARRASCO<br>AGOSTO 2026",
 "foto":"assets/ph-noche.jpg",
 "podio":[["01","Kiki Reboredo / Nico Rosas","1ERA"],["02","...","1ERA"]],
 "sponsors":["BIGG","UES","SANTANDER","DECATHLON"],"acento":"lima"}
```

### `titular` — foto + titular de dos pesos (clases, comunidad, lifestyle)
```json
{"linea1":"Mucho más que","linea2":"PÁDEL","foto":"assets/ph-indoor.jpg",
 "pie":"CARRASCO · HÍPICO · PUNTA DEL ESTE","pos":"top","acento":"blanco"}
```
`linea1` va en Light, `linea2` en Bold. Nunca las dos en el mismo peso. `pos`: `top` o `bottom`.

### `tipografica` — negro + aros (carruseles, frases, humor)
```json
{"lineas":[["TIPOS DE",0],["JUGADORES EN",0],["UN TORNEO",1],["B O S S",2]],
 "pie":"","acento":"lima"}
```
Segundo valor: `0` blanco · `1` acento · `2` acento con tracking abierto.

### `promo` — membresías, beneficios, sponsors
```json
{"kicker":"BOSS CARRASCO","titulo":"HACETE<br>SOCIO.","precio":"6.800","unidad":"/mes",
 "bullets":["Acceso libre toda la semana","Prioridad de reserva"],
 "cta":"QUIERO SER SOCIO","contacto":"Te contactamos por WhatsApp · 097 406 148",
 "fondo":"#1C5D7D","acento":"lima"}
```

### `agenda` — calendario del mes
```json
{"kicker":"CALENDARIO 2026","titulo":"LO QUE<br>SE VIENE.",
 "items":[["28","AGO","Torneo Boss · 28-29-30","CARRASCO"]],
 "pie":"INSCRIPCIONES POR WHATSAPP","acento":"lima"}
```

### `americano` — el partido abierto de la semana
```json
{"kicker":"PARTIDO ABIERTO","dia":"JUEVES","hora":"20:00","fecha":"14 DE AGOSTO",
 "sede":"CARRASCO","nivel":"Cuarta y quinta · mixto","cupos":"6",
 "rotulo_cupos":"LUGARES LIBRES","precio":"890",
 "incluye":["Cancha","Pelotas","Un tostado"],"cta":"ANOTATE","acento":"lima",
 "foto":"assets/decathlon-publico.jpg","foco":"50% 30%"}
```
**No es `torneo` con otra fecha.** Un torneo es un evento de tres días y su placa
es solemne; esto es un jueves a las 20 y tiene que sonar a plan, no a
competencia. Por eso el peso está en el DÍA y la HORA, y los cupos son un
número grande: la urgencia es el argumento.

`foto` es opcional — sin foto sale sobre el azul de marca, que es lo normal un
lunes cuando todavía no hay material nuevo. `cupos` y `precio` desaparecen si
van vacíos, rótulo incluido.

Es la plantilla que más plata deja: los formatos estructurados se venden entre
40 y 50% por encima de la reserva de cancha suelta.

### `socio` — el jugador de la semana
```json
{"rotulo":"JUGADORA DE LA SEMANA","nombre":"Delfina Methol","categoria":"CUARTA",
 "sede":"CARRASCO","datos":[["37","PARTIDOS EN 2026"],["3°","EN EL RANKING"],["2","TÍTULOS"]],
 "frase":"Vengo por el partido y me quedo por el tostado.",
 "foto":"assets/jugadora-actitud.jpg","foco":"50% 26%","acento":"lima"}
```
Es la pieza más barata de alcance que existe: el protagonista la manda a su
grupo. Desde 2026 los **envíos** son la señal de ranking principal de Instagram
— pesan más que los likes.

`datos` admite hasta 3 y es lo que separa un perfil de una foto con un nombre:
sin números no vale la pena hacerla. El nombre se achica solo si es largo.

### `duelo` — el VS: dos cosas enfrentadas

**Ésta es LA plantilla de «VS».** Si el pedido dice *VS*, *versus*, *desafío*,
*duelo*, *X contra Y*, *¿quién gana?* o enfrenta dos cosas de cualquier tipo,
es ésta y no otra. Sirve para dos trabajos distintos:

**1. El desafío o partido** — una dupla contra otra, con la hora en el pie.
```json
{"pregunta":"VIERNES DE DESAFÍO",
 "a":"AGUS ARAUJO<br>PABLO SCIARRA","b":"NICO LANG<br>DIEGO GODÍN",
 "fotoa":"assets/jugador-golpe.jpg","focoa":"50% 30%",
 "fotob":"assets/jugador-azul.jpg","focob":"50% 30%",
 "pie":"HOY 19:30 · BOSS PADEL","acento":"lima"}
```
Cada dupla va en un lado, un nombre por línea con `<br>`. El pie es cuándo y
dónde. El tamaño de los nombres se ajusta solo si son largos.

**2. La pregunta de la semana** — dos opciones y un pedido de comentario.
```json
{"pregunta":"LA PREGUNTA DE LA SEMANA","a":"BANDEJA","b":"VÍBORA",
 "pie":"CONTESTÁ EN LOS COMENTARIOS","acento":"lima"}
```
Pedir un comentario da **+202,78%** de comentarios y una pregunta **+36,70%**,
medido sobre 24 millones de posteos. Es lo más barato de producir del sistema.

Con fotos, agregá `fotoa` / `fotob` (y `focoa` / `focob`). Sin fotos salen dos
bloques de color, que también funciona.

**No armes un VS con `titular`.** Ya pasó: un desafío entre dos duplas salió
como una `titular` con los cuatro nombres apretados en el pie, en letra chica,
porque quien la armó creyó que no había plantilla de VS. La hay: es ésta.

El velo sobre las fotos se **mide**: hay un mínimo de diseño de 0,52 y si la
foto es clara sube solo. No lo toques a ojo.

### `horarios` — las canchas libres del día

**La pieza diaria del club.** Si el pedido enumera horas con precios y canchas
—«los horarios disponibles para mañana», «qué queda libre el sábado»— es ésta.

```json
{"kicker":"VIERNES 8 DE AGOSTO","sede":"HÍPICO","acento":"naranja",
 "nota":"Turno mañana",
 "grupos":[
   {"rotulo":"ABIERTAS · CANCHAS 4 Y 5","precio":"$1.000",
    "horas":["08:00","08:30","09:00","09:30","10:00","10:30","11:00","11:30"]},
   {"rotulo":"TECHADAS · CANCHAS 1, 2 Y 3","precio":"$1.800",
    "horas":[["08:00","3"],["08:30","3"],["10:00","1"],["10:30","1"]]}],
 "cta":"RESERVÁ POR WHATSAPP","contacto":"098 347 637"}
```

**Va en `story`, salvo que pidan otra cosa.** Es contenido que vence en un día:
un posteo de feed sobre los horarios de mañana queda para siempre en la grilla
del perfil, desactualizado desde pasado mañana. La plantilla soporta los cuatro
formatos igual.

**NO uses la plantilla `carrusel` para esto, ni siquiera si el pedido dice
«carrusel».** Pedir un carrusel es pedir *varias imágenes que se leen
deslizando* — eso es un formato, no una plantilla. Si son varias sedes o varios
turnos, hacé **una pieza `horarios` por cada uno**, en `vert`, todas en el mismo
`spec.json`: eso YA es el carrusel, y cada diapositiva es una grilla que se lee
sola. Decilo en `notas.txt` y seguí.

```json
[{"plantilla":"horarios","formato":"vert","nombre":"horarios-carrasco","data":{...}},
 {"plantilla":"horarios","formato":"vert","nombre":"horarios-hipico","data":{...}},
 {"plantilla":"horarios","formato":"vert","nombre":"horarios-punta","data":{...}}]
```

El 7 y el 8/8/2026 salieron cinco carruseles de cinco y seis diapositivas para
los horarios de las tres sedes — dos de ellos con `horarios` ya desplegada. No estaban mal armados
—era lo mejor que se podía con lo que había— pero el contenido se resistía, y se
nota en dos síntomas que conviene reconocer:

1. **Para que entrara hubo que agrupar y perder el dato.** Una diapositiva
   terminó diciendo «08:00 — 11 canchas» en vez de a qué hora hay qué.
2. **Quien mira busca SU hora.** «¿Hay algo a las nueve?» se contesta de un
   vistazo sobre una grilla; en un carrusel obliga a deslizar hasta encontrarla.
   Un carrusel sirve para una idea que avanza. Esto es una tabla, y una tabla
   partida en cinco pantallas deja de ser una tabla.

Tres reglas para llenarla:

- **La hora es el héroe, la cancha no.** Nadie elige «cancha 7 · Radio Disney»:
  elige jugar a las nueve. El número de cancha se decide en la app de reservas.
  Poné los nombres de las canchas en el `rotulo` del grupo si aportan, nunca
  como una lista al lado de cada hora.
- **Agrupá por precio, no por horario.** Hípico no tiene ocho precios: tiene
  dos. Un grupo por precio y todas sus horas adentro.
- **El contador de canchas es opcional y comunica urgencia.** `["09:00","2"]`
  dibuja un `2` chiquito al lado de la hora. Once es «hay lugar»; dos es
  «apurate». Si todas las horas tienen el mismo número, no lo pongas: no dice
  nada y ensucia.

**Las horas no se inventan NUNCA.** El 8/8/2026 salió una pieza con horarios
imaginarios porque el pedido decía «los horarios disponibles» sin listarlos, y
la regla general de esta guía es «no preguntes: decidí». Acá esa regla no
aplica: una placa con disponibilidad inventada manda gente al club a una hora
que no existe. Es el único caso del sistema donde **entregar nada es mejor que
entregar algo**.

Si el pedido no trae las horas concretas, **no generes ninguna pieza**: escribí
sólo `notas.txt` diciendo qué falta —«necesito la lista de horas con su precio
para cada sede»— y terminá. Ese texto le llega tal cual a quien pidió el diseño.

El tamaño de las fichas y la cantidad de columnas se calculan solos según
cuántas horas haya. No los toques.

### `destacada` — portada de historia destacada
```json
{"titulo":"LA SEMANA","icono":"calendario","acento":"lima"}
```
`icono`: `pala` · `calendario` · `trofeo` · `pin` · `chat` · `ranking` ·
`reloj` · `aros`.

Instagram recorta la portada **en un círculo desde el centro**, así que todo
vive adentro de un círculo imaginario y nada se apoya en los bordes. Se ven a
unos 64 píxeles en el perfil: por eso el ícono y el texto son
desproporcionadamente grandes en la placa de 1080. Está bien así.

Las siete de Boss: **CARRASCO · HÍPICO · PUNTA · LA SEMANA · TORNEOS ·
RANKING · RESERVAR**. Los cuatro clubes del mundo que mejor comunican tienen
las destacadas así, como secciones permanentes, con una por sede.

### `countdown` — cuenta regresiva
```json
{"dias":"3","kicker":"TORNEO BOSS<br>CARRASCO","fecha":"28, 29 Y 30 DE AGOSTO",
 "sede":"CARRASCO","cta":"ÚLTIMOS CUPOS","contacto":"097 406 148",
 "foto":"assets/decathlon-publico.jpg","acento":"lima"}
```
`contacto` vacío saca también el rótulo «INSCRIPCIONES AL». No dejes el rótulo
colgando sin número.

### `campeones` — campeones por categoría
```json
{"titulo":"CAMPEONES","sede":"BOSS CARRASCO · AGOSTO",
 "filas":[["1ERA","Reboredo / Rosas"],["4TA","Methol / Pérez"]],
 "foto":"assets/jugador-azul.jpg","pie":"","acento":"lima"}
```
Distinta de `resultados`: acá van los ganadores de cada categoría, no el podio
de una sola. `foto` es opcional.

### `tip` — contenido educativo
```json
{"kicker":"CONSEJO DEL PROFE","titulo":"LA BANDEJA<br>NO ES UN SMASH.",
 "cuerpo":"Es un golpe de control...","firma":"POR MARTÍN, PROFE DE CARRASCO",
 "fondo":"#123C51","acento":"lima"}
```
Rinde mucho más como carrusel de 3 o 4 que como placa suelta.

## El logo

`assets/boss-logo.svg` es el **archivo oficial del club** (extraído del original). `brand.py` lo inserta vectorial y le cambia el color en tiempo de render — no hay que tocarlo.

- Color original de marca: **navy `#1B365D`**. Sobre fondo oscuro va en blanco `#FAFAFA`.
- El wordmark `BOSS` es **outline puro, sin marco ni caja**. Nunca rellenarlo en sólido.
- Proporción fija 2.805 : 1. Ancho habitual 150–230 px en pieza de 1080.
- En `logo/` están las 4 variantes sueltas (navy, blanco, negro, lima) en SVG y PNG transparente, más el PDF original.

## Presentaciones en PDF

Cuando el pedido incluye el formato `pdf`, o cuando el texto pide claramente
un documento ("una presentación para el sponsor", "algo para mandarle a la
marca", "una propuesta"), la pieza es una presentación, no una placa.

```bash
python3 render.py spec.json /ruta/de/salida   # un job con "plantilla": "presentacion"
```

```json
{"plantilla":"presentacion","nombre":"propuesta-sponsor","data":{
  "acento":"lima","fecha":"Agosto 2026","pie":"bosspadel.uy · @boss.padel",
  "slides":[ ... ]}}
```

### Los siete tipos de slide

| `tipo` | Campos | Para qué |
|---|---|---|
| `portada` | `kicker`, `titulo`, `bajada`, `foto`, `foco` | Siempre la primera |
| `seccion` | `kicker`, `titulo`, `bajada` | Separador entre bloques |
| `contenido` | `kicker`, `titulo`, `texto`, `puntos[]`, `foto`, `foco` | El caballito de batalla |
| `datos` | `kicker`, `titulo`, `datos[[cifra, rótulo]]` | Cifras grandes |
| `tabla` | `kicker`, `titulo`, `filas[[izq, der]]` | Planes, precios, comparaciones |
| `foto` | `kicker`, `titulo`, `bajada`, `foto`, `foco` | Respiro visual a sangre |
| `cierre` | `titulo`, `lineas[]`, `foto`, `foco` | Siempre la última |

El `foco` sale de `referencias/fotos.json` igual que en las placas, pero usá
el valor de **`story`**: la presentación es apaisada, así que recorta por el
mismo eje que una historia.

### Cómo se estructura una propuesta

Entre 6 y 9 slides. Más que eso no lo lee nadie.

1. **Portada** — una frase, no un párrafo. Foto con la persona a un lado.
2. **Sección o datos** — quiénes somos, en cifras. Los números convencen más
   rápido que los adjetivos.
3. **Contenido** — qué es el club de verdad. Bullets cortos, máximo cinco.
4. **Foto** — un respiro. Acá va la mejor foto que tengas del tema.
5. **Tabla** — qué se ofrece concretamente. Sin esto, la propuesta no cierra.
6. **Cierre** — mail, teléfono, redes. Siempre.

### Reglas

- **Una idea por slide.** Si un slide necesita dos títulos, son dos slides.
- **Cifras verificables.** Si no sabés cuántas canchas tiene una sede, no la
  inventes: sacala del bloque de datos del club de más abajo, o dejala afuera
  y decilo en `notas.txt`.
- **Los bullets son frases, no párrafos.** Máximo dos renglones cada uno.
- **La portada no lleva bajada larga.** Una línea de contexto y nada más.
- El cuerpo del titular de portada se ajusta solo según el largo, pero un
  titular de más de ocho palabras va a salir chico igual: escribilo corto.

## Carruseles y secuencias de stories

Un carrusel es **una pieza que se lee deslizando**, no cinco placas sueltas.
Una secuencia de stories es otra cosa distinta: varias stories que se ven una
atrás de otra tocando la pantalla.

```bash
python3 render.py spec.json /ruta/de/salida
```

```json
{"plantilla":"carrusel","formato":"vert","nombre":"podio-agosto","data":{
  "acento":"lima",
  "slides":[
    {"tipo":"portada","kicker":"TORNEO BOSS · AGOSTO","titulo":"ASÍ QUEDÓ<br>EL PODIO",
     "bajada":"Una línea de contexto.","foto":"assets/x.jpg","foco":"50% 26%"},
    {"tipo":"puesto","puesto":"03","detalle":"1RA CATEGORÍA","nombres":"Fulano<br>Mengano"},
    {"tipo":"puesto","puesto":"01","detalle":"1RA CATEGORÍA","nombres":"Kiki<br>Nico","foto":"..."},
    {"tipo":"cierre","kicker":"GRACIAS A TODOS","titulo":"NOS VEMOS<br>EN LA PRÓXIMA.",
     "cta":"GUARDÁ ESTE POSTEO","texto":"El próximo se viene en septiembre."}
  ]}}
```

Los archivos salen **numerados**: `podio-agosto-01.png`, `-02`, `-03`. Ese
número es lo único que garantiza que quien los suba a Instagram no publique el
podio al revés. No los renombres.

### Los cinco tipos de diapositiva

| `tipo` | Campos | Para qué |
|---|---|---|
| `portada` | `kicker`, `titulo`, `bajada`, `foto`, `foco` | **Siempre la primera** |
| `puesto` | `puesto`, `detalle`, `nombres`, `rotulo`, `foto`, `foco` | Podio. `puesto:"01"` sale en acento sólido y rotulado CAMPEONES; el resto en outline |
| `punto` | `numero`, `detalle`, `titulo`, `texto`, `foto`, `foco` | Un ítem de una lista o de un consejo |
| `texto` | `kicker`, `titulo`, `texto` | Tipográfica sobre negro. Respiro entre dos con foto |
| `cierre` | `kicker`, `titulo`, `cta`, `texto`, `foto` | **Siempre la última** |

`foto` es opcional en todos menos `portada`. **Alterná**: cinco fotos seguidas
cansan y el banco tampoco da. Una con foto, una sin, es buen ritmo.

### Las reglas, y de dónde salen

Los datos son de Metricool sobre 24,3 millones de posteos en 375.000 cuentas.

- **Entre 3 y 6 diapositivas.** El límite duro del código es 10 y el de
  Instagram 20, pero nadie desliza tanto.
- **La portada carga todo el peso.** Es la única que se ve en el feed sin
  deslizar. Si no gana ahí, el resto no existe.
- **El cierre pide GUARDAR, no seguir.** El carrusel genera **nueve veces más
  guardados** que una foto sola, y el guardado es la señal que más pesa para
  que Instagram lo siga mostrando. Pedir seguidores en la última desperdicia el
  único lugar donde la gente que llegó hasta el final va a hacer algo.
- **Una idea por diapositiva.** Si necesita dos titulares, son dos.
- **El texto de cuerpo, dos renglones como mucho.** Nadie lee un párrafo
  deslizando.
- **La foto suelta se está hundiendo** —alcance −22%, interacciones −25%,
  engagement −46% interanual—. Ante la duda entre una placa sola y un carrusel
  de tres, el carrusel.

### La proporción no se elige por diapositiva

`formato` va **una vez, en el trabajo**, y todas las diapositivas lo heredan.
Instagram recorta cada imagen a la proporción de la primera: un carrusel
mezclado sale con placas cortadas. El código lo impone, pero no intentes
pasarle un `formato` por diapositiva porque lo va a ignorar.

Por defecto **`vert`** (1080×1350): ocupa más pantalla en el feed que el
cuadrado, que es la única forma de ganar atención antes del deslizamiento. Usá
`post` sólo si el pedido pide cuadrado explícitamente.

### Secuencias de stories

**No es un carrusel.** Son stories separadas, se avanzan tocando, y cada una
tiene unos dos segundos de atención real.

```json
{"plantilla":"secuencia","nombre":"seq-torneo","data":{
  "acento":"lima",
  "slides":[
    {"kicker":"ESTE FIN DE SEMANA","titulo":"SE VIENE<br>EL TORNEO.",
     "texto":"28, 29 y 30 · Carrasco","foto":"assets/x.jpg","foco":"50% 26%","cuerpo":118},
    {"kicker":"LIBRES Y FEMENINA","titulo":"QUEDAN<br>6 CUPOS.","texto":"..."},
    {"kicker":"INSCRIPCIONES","titulo":"¿TE<br>ANOTÁS?","texto":"...",
     "foto":"...","responder":"Respondé este mensaje"}
  ]}}
```

No lleva `formato`: siempre 1080×1920. `cuerpo` es el tamaño del titular en px
(112 por defecto); bajalo si el texto es largo.

Las reglas salen de 161.180 stories analizadas por Socialinsider:

- **Tres cuadros.** La primera pierde el **23,8% de la gente** —es el peor
  cuadro de toda la secuencia— y entre el 57% y el 67% de los que quedan
  avanzan tocando. Cinco cuadros no los ve nadie.
- **Un titular de 2 a 4 palabras por cuadro.** En dos segundos no se lee más.
- **El último invita a responder**, con el campo `responder`. Las respuestas a
  stories crecieron **88% interanual**, el mayor salto de cualquier métrica de
  Instagram este año, y una respuesta abre una conversación privada — que para
  un club que vende clases y torneos vale mucho más que un like.
- El titular arranca fuerte en el primero: es donde se pierde la gente.

## Reels en video

`video.py` corta tramos de varios clips y fotos y los pega en un reel vertical
de 1080×1920 a 30 fps. El renderizador es ffmpeg, pero las placas de entrada y
de cierre las dibuja Chromium con las plantillas de siempre — así el reel
empieza y termina con la misma tipografía que las placas.

```bash
python3 render.py placas.json    # primero las tapas, si el reel lleva
python3 video.py reel.json /ruta/de/salida
```

```json
{"nombre":"torneo-femenino","tramos":[
  {"tipo":"placa","archivo":"out/reel-entrada.png","dura":1.8},
  {"tipo":"foto","archivo":"assets/jugadora-saque.jpg","dura":2.4,
   "texto":"Faltan 3 días","zoom":1.14},
  {"tipo":"video","archivo":"clips/EH2A3321.mp4","desde":0.3,"dura":2.4,
   "recorte":1.15,"foco_x":0.45},
  {"tipo":"placa","archivo":"out/reel-cierre.png","dura":2.4}
]}
```

### Con clips que subió la persona: el GUION DE EDICIÓN

Cuando el material lo sube la persona —lo normal—, el reel **no se pide con el
spec de arriba: se pide con un guion**. La diferencia es cómo se expresa cada
tramo:

| | |
|---|---|
| El spec | `desde` + `dura` — cuánto ocupa en el reel |
| El guion | `desde` + `hasta` — **el punto de entrada y el de salida del clip original** |

El guion es como pensás cuando estás mirando el material: «esto sirve del 12,4
al 16,1». La traducción la hace el motor.

```json
{"nombre":"reel-torneo",
 "tramos":[
   {"archivo":"clips/subidas/01-partido.mp4","desde":12.4,"hasta":16.1},
   {"archivo":"clips/subidas/01-partido.mp4","desde":31.0,"hasta":34.2,"velocidad":0.5}
 ],
 "musica":{"archivo":"clips/subidas/03-pista.mp3","volumen":0.35}}
```

```bash
python3 video.py guion.json /ruta/de/salida
```

`video.py` se da cuenta solo de cuál de los dos le pasaste.

### El análisis ya viene hecho: NO lo repitas

Cuando alguien sube clips, el worker los analiza antes de llamarte y te deja en
el prompt, por cada archivo: duración, medidas, **dónde cambia la toma**,
**dónde hay silencio** y **dónde están los picos de audio**. Más una carpeta
`clips/subidas/analisis/` con cuadros ya extraídos, con el segundo en el nombre.

**No corras `ffprobe` ni `ffmpeg` para averiguar nada de eso.** Ya está, y cada
llamada de más es un turno que se relee entero en todos los que siguen.

Lo que **sí** tenés que hacer es **abrir los cuadros con Read antes de elegir
los cortes**. Sin mirarlos estás editando a ciegas, y se nota.

Tres cosas que el análisis te da servidas:

- **Cortá en los cortes de toma.** Cortar en el medio de una toma se nota;
  cortar donde el video ya cambiaba, no.
- **Saltá los silencios.** Es lo que más hace que un video de celular parezca
  editado.
- **Los picos de audio son casi siempre el momento bueno**: el golpe, la risa,
  el «mirá esto».

### Se valida antes de encodear

Un encode tarda minutos. Si un tramo pide un segundo que no existe, o el reel
se pasa de 90 segundos, el guion falla **antes**, con el motivo en castellano y
todos los problemas juntos. Los avisos con ⚠ no frenan nada, pero leelos: un
tramo de menos de 0,8 s no es un corte, es un parpadeo.

`velocidad` menor a 1 es cámara lenta. **Ese tramo va mudo a propósito** —el
audio estirado suena a dibujo animado—, así que no lo uses donde alguien habla.

### Los tres tipos de tramo

| `tipo` | Campos | Notas |
|---|---|---|
| `foto` | `archivo`, `dura`, `texto`, `zoom` | Siempre lleva acercamiento: una foto quieta se lee como que el video se colgó |
| `video` | `archivo`, `desde`, `dura`, `texto`, `recorte`, `foco_x`, `audio` | `desde` es el segundo donde empieza el corte |
| `placa` | `archivo` (un PNG ya renderizado), `dura` | Para entrada y cierre |

### El encuadre de un clip apaisado

Una cámara filma en 16:9 y el reel es 9:16. Recortar directo deja un tercio del
ancho y parte la cancha al medio: se pierden dos jugadores. Dejarlo entero
tampoco sirve: a ancho completo ocupa el 32% del alto y se ve como una tirita.

Lo resuelve `recorte`, la proporción a la que se lleva la fuente antes de
agrandarla a ancho completo:

- **`0.5625` (por defecto) — el clip llena el cuadro entero.** El reel es
  vertical y todo tiene que verse vertical: es lo que corresponde salvo que
  haya una razón concreta para lo otro.
- `1.0` — cuadrado, ocupa el 56% del alto y aparecen bandas desenfocadas
  arriba y abajo. Sólo para un punto donde de verdad importe ver la cancha
  entera y los cuatro jugadores.
- `foco_x` mueve el recorte de lado: `0` todo a la izquierda, `0.5` centro,
  `1` a la derecha. Con el recorte lleno se pierde mucho ancho, así que este
  valor **importa**: úsalo para dejar al jugador dentro del cuadro.

Cuando queda hueco, se llena con el mismo clip desenfocado y encima va
`assets/velo-reel.png`, un degradé real. **No uses `drawbox` para oscurecer:**
pinta alfa constante y deja un borde recto bien visible cruzando la imagen.

### La calidad de un clip recortado a vertical

Recortar 16:9 a 9:16 deja 608 px de ancho que hay que estirar a 1080: un
aumento de **1,78×**. Sin cuidado, el tramo de video queda blando al lado de
las fotos, que son nítidas — medido con varianza del laplaciano, 11 contra 113.

Tres cosas lo arreglan y las tres están puestas:

- **Escalar con `flags=lanczos`**, que conserva bastante más borde que el
  escalador por defecto.
- **`unsharp` suave después** de agrandar (`luma_amount=0.9`). Pasarse hace
  aparecer halos alrededor de los jugadores, que se ve peor que la imagen
  blanda: si el número de nitidez sube mucho por encima del de las fotos,
  hay que mirar un recorte al 100% antes de darlo por bueno.
- **Partir del original, no de una copia comprimida.** Cada recompresión
  intermedia se paga en el resultado, y el recorte a vertical la amplifica.

Con eso el tramo de video pasó de 11 a 156.

### Nada se estira, nunca

Todo tramo sale en 1080×1920 sin deformar. Dos lugares donde es fácil romperlo:

- En una foto hay que **recortar a 9:16 antes del acercamiento**. Si se hace al
  revés, `zoompan` toma una región con la proporción de la foto original y la
  mete a la fuerza en el cuadro: la imagen sale aplastada un 16% a lo ancho y
  la gente se ve más flaca y más alta.
- Una `placa` que no venga exactamente en 9:16 se encaja y se completa con el
  negro de la marca. Nunca `scale=1080:1920` a secas.

El encuadre de las fotos **no se decide acá**: sale del valor `story` de
`referencias/fotos.json`, que es la misma proporción. Así una jugadora se ve
igual en la placa y en el reel.

### Los rótulos: cómo ENTRA el texto

Un reel deportivo se reconoce por cómo entra el texto, no por qué dice. Los
rótulos ya no son un PNG con un fundido: los dibuja Chromium **cuadro por
cuadro** con animación CSS de verdad, y ffmpeg los superpone.

Cada tramo elige su estilo con `estilo`:

| `estilo` | Cómo entra | Cuándo |
|---|---|---|
| `pop` | Salta con rebote y se asienta | El de siempre. Sirve para todo |
| `palabra` | Las palabras aparecen una atrás de otra | Frases de 3 o 4 palabras. Es el que más «edita» |
| `barrido` | Una barra del color de acento barre y revela el texto detrás | Titulares cortos. El más deportivo |
| `bloque` | Pastilla sólida de acento que crece desde el centro | Llamados a la acción: ANOTATE, ÚLTIMOS CUPOS |

```json
{"archivo":"clips/subidas/01.mp4","desde":0.6,"hasta":3.4,
 "texto":"El finde se juega","estilo":"palabra","pos":"arriba"}
```

**Una entrada bien puesta le gana a diez efectos juntos.** Ninguna dura más de
0,46 s y ninguna sigue moviéndose después: el texto tiene que quedar quieto y
legible al menos medio segundo. No pongas un estilo distinto en cada tramo —
elegí uno para el reel y usá `bloque` sólo en el cierre.

### `encuadre`: cuándo NO recortar

Un punto de pádel filmado de lejos es **una unidad**: los cuatro jugadores, la
pelota y las paredes. Llevarlo a 9:16 recortando se lleva un tercio del ancho y
con él la mitad de lo que hace que la jugada se entienda.

Para eso está `encuadre: "marco"`. El clip queda **entero y centrado**, y el
espacio que sobra arriba y abajo no es relleno: es la parte gráfica de la
pieza. Arriba el logo del club, abajo el título, y un filo de acento pegando el
video al marco.

```json
{"archivo":"clips/subidas/jugada.mp4","desde":0.4,"hasta":4.0,
 "encuadre":"marco","texto":"Joaquín Rodríguez","estilo":"palabra","pos":"abajo"}
```

**La ventaja no es sólo estética: en el marco el texto NO tapa la jugada.**

| `encuadre` | Cuándo |
|---|---|
| `lleno` (por defecto) | Planos cerrados: una cara, un golpe, alguien hablando. El sujeto ocupa el centro y lo de los costados no importa |
| `marco` | **Jugadas.** Cualquier plano donde la acción cruza la cancha, y todo material cuadrado |

Lo que **no** se usa más es `recorte` mayor a 1, que metía bandas
desenfocadas. Si el clip no entra recortado, va en `marco`.

### La imagen LLENA el cuadro

Miré los reels de Premier Padel: **los ocho llenan el cuadro entero**. Ninguno
tiene bandas borrosas arriba y abajo. Ese look quedó viejo.

Por eso `recorte` **no se toca salvo que haya un motivo**. Sin él, el clip llena
los 1080×1920 y se pierde ancho de cancha — que es el precio correcto. Para
elegir QUÉ ancho se conserva está `foco_x`: 0.5 es el centro, 0.35 corre el
encuadre a la izquierda, 0.65 a la derecha. **Mirá los cuadros del análisis y
elegí el foco; no pongas bandas.**

`recorte` mayor a 1 deja ver casi todo el ancho pero mete las bandas
desenfocadas. Se justifica en un caso y medio: un punto largo donde se pierden
dos jugadores, o material apaisado donde la acción cruza toda la cancha.

### El texto en pantalla NO es lo que escribió la persona

**Es la regla más importante de un reel y la que más fácil se rompe.**

Quien pide te da una idea, no un guion. Si escribe *«que diga: Hoy, les
presentamos a Joaquín Rodríguez, el mago del mes»*, eso es el **encargo**. Vos
sos el editor: tenés que convertirlo en carteles.

> ✗ Tramo 1: «HOY LES PRESENTAMOS A» · Tramo 2: «JOAQUIN RODRIGUEZ» ·
>   Tramo 3: «EL MAGO DEL MES»
>
> Es la frase partida en pedazos. Ninguno de los tres dice nada solo, el
> primero es puro relleno, y el tercero llega cuando la jugada ya terminó.

> ✓ Tramo 1 (arranca la jugada): «MIRÁ ESTO» · Tramo 2 (el punto): sin texto,
>   que se vea la jugada · Tramo 3 (el remate): «EL MAGO **DEL MES**» ·
>   Tramo 4 (festejo): «JOAQUÍN RODRÍGUEZ»
>
> El nombre llega DESPUÉS del golpe, que es cuando alguien quiere saber quién
> fue. Y el primer cartel no explica: engancha.

Las reglas concretas:

- **2 a 4 palabras por cartel.** No es un subtítulo, es un cartel. Más de 5 y
  el validador te avisa.
- **Nunca el mismo texto en dos tramos seguidos.** La animación de entrada
  vuelve a correr y el reel se siente trabado. Si el texto tiene que quedarse,
  **alargá el tramo**, no lo repitas.
- **No todos los tramos llevan texto.** El punto se mira, no se lee. Alternar
  con y sin es lo que da respiración.
- **El primer cartel engancha, no presenta.** «HOY LES PRESENTAMOS A» es
  exactamente lo que hace que alguien deslice.
- **El nombre va después del golpe**, no antes.
- Escribí en el tono del club: voseo, corto, sin punto final.

Y decí en `notas.txt` qué texto te dieron y qué carteles escribiste, para que se
pueda discutir.

### La música que sube la persona manda

Si en el análisis aparece un archivo de audio subido, **usá ese** y no la cama
sintetizada:

```json
"musica": {"archivo": "clips/subidas/02-pista.mp3", "volumen": 0.35}
```

La cama del motor es el respaldo para cuando no mandan nada. Nunca la elijas
por encima de una pista que la persona se tomó el trabajo de adjuntar.

El golpecito del rótulo se puede apagar con `"sonido": {"rotulos": false}` —
en una pieza con alguien hablando molesta más de lo que suma.

### Reglas de ritmo y duración

Estas no son preferencias: salen de datos, y el detalle está en el documento
«Audio y reels — tendencias» del proyecto.

- **12 segundos, no 20.** El estudio de Metricool sobre 24,3 millones de
  posteos da un tiempo promedio de visualización real de **8,5 segundos**, y
  **hasta la mitad de la gente abandona antes del cuarto segundo**. Un reel de
  20 segundos con el remate al final no lo ve casi nadie. El rango útil para
  llegar a quien no sigue la cuenta es **7 a 15 segundos**.
- **El gancho va primero.** El tramo más fuerte —movimiento, acción, la noticia—
  arranca el reel. Nunca abrir con una placa tipográfica: frena el ritmo justo
  en la zona donde la gente se va.
- **Todo lo importante resuelto antes del segundo 8.** Lo que venga después es
  para quien ya se quedó.
- **Tramos de 1 a 1,5 segundos en el medio**, y sólo la entrada y el cierre
  respiran más.
- **Texto de 2 o 3 palabras.** Los reels del club dicen «ÚLTIMO PUNTO»,
  «SER PARTE», «CADA CLASE SUMA». Nunca una frase larga.
- **No en todos los tramos va texto.** Alternar con y sin da respiración.
- **El reel tiene que funcionar mudo.** El 86% de los usuarios de Spotify
  silencia el video de otras plataformas. Si el mensaje sólo está en el audio,
  no llegó. Los rótulos tienen que contar la historia solos.

### Sonido y música

`sonido.py` genera **todo por síntesis**: no descarga nada. Cuatro efectos —
`whoosh`, `pop`, `impacto`, `riser` — que el motor coloca solo: whoosh antes de
cada corte, impacto encima, pop con cada rótulo, y un riser que desemboca en el
cierre.

**La música va PRENDIDA por defecto desde el 4/8/2026.**

Antes iba apagada, y el razonamiento era bueno mientras duró: Instagram
restringe su biblioteca musical por tipo de cuenta —una cuenta de Empresa queda
limitada a la Meta Sound Collection—, así que convenía entregar el reel con el
sonido de cancha y agregarle la música en la app al publicar, donde la licencia
ya está resuelta.

**Ese razonamiento se cayó cuando el sistema empezó a publicar por API.** Por la
API de Instagram **no se puede agregar música de su biblioteca**: ni sonidos en
tendencia, ni catálogo. Un reel que sale por ahí sale con el audio que tenga el
archivo. Si la música no va adentro, no va.

Y se puede meter adentro sin ningún problema de licencia justamente porque es
sintetizada: la cama es nuestra.

#### Los tres ánimos

| `animo` | Cómo suena | Para qué |
|---|---|---|
| `club` | La menor, con palmas, 100 bpm | El de esta marca. Enérgico sin ser alegre |
| `calmo` | Do mayor, sin palmas, 84 bpm | Marcas de servicio. Acompaña, no compite con una voz |
| `tension` | La menor con tensión, 112 bpm | Cuentas regresivas y anuncios |

Cada marca declara el suyo y no hay que elegirlo en cada pieza. En el guion se
puede pisar sólo si el contenido lo pide:

```json
"musica": {"animo": "tension", "bpm": 108, "volumen": 0.30}
```

`volumen` por defecto es 0.35. Medido sobre un reel real, la cama sube la banda
grave un 32% y apenas toca los agudos: se siente el pulso sin tapar el sonido
de cancha. **Arriba de 0,60 tapa una voz**, y el validador avisa si el reel
tiene subtítulos.

Con `"musica": {"volumen": 0}` o `"sonido": {"musica": false}` se apaga, para el
reel que se va a publicar a mano y al que le van a poner audio en tendencia
desde el celular.

## Efectos atmosféricos

Cuando el pedido describe un clima o una atmósfera —«que llueva», «como si
fuera una ventana con gotas», «con niebla»— se resuelve con `efectos.py`. No
hay que buscar una textura ni abrir un editor: se agrega un campo al `data` de
cualquier plantilla.

```json
{"foto":"assets/jugadora-resto-azul.jpg","foco":"50% 26%",
 "efecto":["vidrio"], "efecto_fuerza":1.0}
```

`efecto` acepta uno o varios. `efecto_fuerza` va de 0,3 a 1,7 (1 por defecto).

### Cuándo NO poner un efecto — leer antes que la tabla

**Un efecto se aplica sólo si el pedido habla de cómo tiene que VERSE la pieza.
Nunca por iniciativa propia.**

La trampa es que la misma palabra puede estar en dos lugares muy distintos:

| El pedido dice | Qué es | ¿Efecto? |
|---|---|---|
| «que el fondo se vea como una ventana con gotas» | instrucción visual | sí |
| «que llueva en la foto», «con niebla» | instrucción visual | sí |
| «una placa que **diga**: no te quedes mirando la lluvia» | la palabra es parte del TEXTO a imprimir | **no** |
| «un posteo sobre el día de lluvia» | es el tema, no una indicación de diseño | **no** |

Si la palabra aparece dentro de lo que hay que escribir en la placa, es
contenido, no diseño. Pasó de verdad: un pedido que decía «que diga: no te
quedes mirando la lluvia» salió con estelas de lluvia encima de una foto que
**ya tenía** una ventana mojada. Doble lluvia, y ninguna pedida.

Dos reglas más:

- **Si la persona subió una foto, mirala antes.** Si ya tiene lluvia, gotas,
  niebla o el clima que sea, no le sumes el efecto encima. Para eso la subió.
- **Ante la duda, no.** Una pieza sin efecto se ve normal; una con un efecto
  que nadie pidió se ve rara y hay que rehacerla. Si te parece que un efecto la
  mejoraría, **no lo apliques: proponelo** en `notas.txt`, para que lo pidan
  en la próxima si les gusta.

| Efecto | Qué hace | Lo pide un texto que diga |
|---|---|---|
| `vidrio` | Gotas sobre un vidrio, con la foto desenfocada detrás | «ventana con gotas», «vidrio mojado», «empañado», «llovido» |
| `lluvia` | Estelas diagonales por encima de todo | «que llueva», «día de lluvia», «diluvio» |
| `niebla` | Bruma que sube desde abajo | «niebla», «neblina», «misterioso» |
| `destello` | Haz de luz en diagonal | «reflejo», «rayo de luz», «brillo» |
| `grano` | Grano de película, muy sutil | «analógico», «vintage», «textura» |

Se combinan: `["vidrio","lluvia"]` es la ventana mojada **y** lloviendo afuera.
`["niebla","grano"]` da una cancha vacía con clima.

### Cómo están hechos, por si hay que tocarlos

Todo es CSS y SVG dentro del mismo Chromium. Nada de PNG de textura: se
estiran a cualquier formato sin perder nitidez y cada pieza sale distinta.

- **`vidrio`**: cada gota es una **lente**, no una mancha. Es un círculo con la
  misma foto de fondo, ampliada un 35% y desplazada para coincidir justo con lo
  que tapa, más un brillo abajo y una sombra arriba. El fondo va desenfocado.
  El primer intento fue recortar la foto con una máscara de ruido y las gotas
  salieron como rayones — una gota muestra el fondo nítido, por eso no funciona
  como recorte.
- **`lluvia`**: gradiente horizontal para las líneas finas y máscara vertical
  para los trazos. Hacen falta los dos ejes: un gradiente vertical con
  `background-size` angosto **no tila**, porque el gradiente sólo varía en
  vertical y repetir columnas reproduce la misma banda. Sale una persiana.
- Los trazos van largos y con períodos bien distintos entre capas, o se forman
  hileras alineadas que delatan el truco.

### Dónde se inyectan

`render.py` los mete **justo después del `<img class="bg">`**. Las plantillas no
usan `z-index`, así que manda el orden del documento: ahí el efecto queda encima
de la foto y debajo del scrim y del titular. Como primer hijo del canvas la foto
lo taparía entero.

## Fotos y videos que sube la persona

Si el pedido trae material propio, llega separado y el prompt lo lista:

- las **fotos** en `assets/subidas/`
- los **clips** en `clips/subidas/`

**Usá ese material y no el del banco.** Lo subió a propósito; el banco es para
cuando no hay material propio, no una alternativa a considerar.

### Con clips subidos, antes de cortar: mirá qué hay adentro

Un clip de cámara no viene con descripción y el nombre del archivo no dice
nada. Dos comandos antes de decidir los cortes:

```bash
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 clip.mp4
ffmpeg -v error -y -ss 1.0 -i clip.mp4 -frames:v 1 /tmp/c1.jpg
```

Sacá tres o cuatro cuadros repartidos a lo largo del clip, armá una hoja de
contacto con `herramientas/hojas.py` y miralos. **Nunca elijas un tramo por el
nombre del archivo**: ya pasó que cuatro clips que parecían de juego eran el
perro del club y gente sentada en el lounge.

Con la duración en la mano, elegí los tramos: `desde` es el segundo donde
empieza el corte y `dura` cuánto se usa. Si un clip dura 1,2 segundos no le
pidas 2 segundos — el tramo sale corto y el reel se desfasa.

Los clips subidos van sí o sí. Si no alcanzan para los 12 segundos, completá
con fotos del banco, pero que el material propio sea el protagonista.

Lo único que hay que resolver a mano es el encuadre: una foto subida no tiene
`foco` precalculado en `fotos.json`. Generá la pieza, **mirá el PNG que salió**,
y si la cara quedó cortada o chocando con el titular, corregí el `foco` y volvé
a generar. `herramientas/foco.py` sirve para ver los cuatro recortes de una vez.

## Datos fijos del club

| Sede | Canchas | Teléfono |
|---|---|---|
| Carrasco (principal) | 14 | 097 406 148 |
| Hípico (Ciudad de la Costa) | 5 | 098 347 637 |
| Punta del Este | 4 | 098 238 541 |

Mail: info@bosspadel.com · Web: bosspadel.uy · IG: @boss.padel · Reservas: WONA Sport App
Sponsors: BIGG · UES · Radio Disney · Santander · Zillertal · Gatorade · Decathlon · exhala

## Al entregar

- Los archivos quedan en la carpeta de salida que te pasaron. No hay que
  mandarlos a ningún lado: el worker los sube solo cuando terminás.
- Escribí el **caption sugerido** en el estilo del club: voseo, frases cortas,
  1-2 emojis (🎾 🔥 ⚡️ ✨). **Sin teléfono**, salvo que el pedido lo pida, y
  **sin hashtags** (ver «Antes de elegir el formato»).
- **El caption termina con una pregunta o un pedido de comentario.** No es un
  adorno: es lo que más mueve el alcance de todo el sistema. «¿Bandeja o
  víbora? Contestá acá abajo» vale más que «Nos vemos en la cancha!».
- Si usaste fotos placeholder, decilo en una línea.

## Los nombres de archivo van en ASCII

`nombre` en el spec es el nombre del archivo. **Sin ñ, sin tildes, sin signos
de pregunta ni de exclamación.** `story-nos-vemos-manana`, no
`story-nos-vemos-mañana`.

Supabase Storage rechaza esas claves con un 400 y el diseño se pierde **después
de haberse generado bien**. El worker ahora limpia el nombre antes de subir,
así que aunque te olvides no se rompe — pero el archivo va a salir con el
nombre traducido y es mejor que lo elijas vos.

Los acentos en el TEXTO de la pieza no tienen nada que ver: ahí van todos.

## Errores a evitar

- Fondo blanco (la marca vive en oscuro).
- Rellenar el `BOSS` del logo en sólido — va siempre en outline.
- Lima y naranja compitiendo como titulares en la misma pieza.
- Foto con texto encima sin scrim: ilegible.
- Titular de dos líneas en el mismo peso tipográfico.
- Anunciar un torneo y no publicar después el podio.
- Armar un VS o un desafío con `titular` y meter los nombres en el pie: para
  eso está `duelo`.
- Armar los horarios libres como carrusel: para eso está `horarios`, que los
  muestra todos juntos en una grilla que se lee de un vistazo.
- Escribir en `notas.txt` que una plantilla «no existe» sin haber leído la lista
  de las 13. Si de verdad falta, decilo nombrando qué haría falta — pero
  primero fijate.
- Meter el teléfono en una pieza que no lo pidió.
- Agregar un efecto atmosférico que nadie pidió, o aplicarlo porque la palabra
  «lluvia» aparecía en el texto que había que imprimir.
