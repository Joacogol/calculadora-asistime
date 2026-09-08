---
name: clinica-preventiva-disenos
description: Genera piezas de redes para Clínica Preventiva (clínica de salud laboral y análisis clínicos en Uruguay — sedes Montevideo y Ciudad de la Costa) con la identidad real de la marca: logo oficial vectorial, rojo pantone 032 #EB3141, gris 70% negro #6D6E70, tinta #181715, tipografía Montserrat, y 5 plantillas reconstruidas de las piezas que publica la cuenta (foto lateral, foto a sangre, recorte sobre claro, tipográfica, convenio con empresas). Incluye carruseles, secuencias de stories, reels en video y presentaciones. Usar SIEMPRE que pidan "una placa / arte / post / flyer / diseño para Clínica Preventiva", "algo de carné de salud / psicotécnico / libreta de conducir / aptitud física / análisis clínicos / medicina laboral", "un carrusel o una story para la clínica", cuando pidan "un convenio / un cupón / un acuerdo con una empresa" y suban el logo de esa empresa, o cuando mencionen @clinica.preventiva, clinicapreventiva.com, o las sedes de Gral. Flores o Costa Urbana Shopping en contexto de diseño o contenido.
---

# Diseños Clínica Preventiva

Todo se renderiza con Chromium a través de `render.py`. El motor —Chromium,
ffmpeg, sonido, efectos, la estructura del carrusel— vive en `motor/` y es
compartido con las otras marcas del sistema. **No entres ahí:** no hay nada que
ajustar por pieza, y cada archivo que abrís se relee entero en todos los turnos
que siguen.

## El camino corto

1. elegir plantilla y foto
2. escribir un `spec.json` con un trabajo por formato pedido
3. `python3 render.py spec.json <carpeta-de-salida>`
4. escribir `copy.txt` (sólo el texto del posteo) y `notas.txt`

### `copy.txt` y `notas.txt` son dos archivos distintos

**`copy.txt` sale publicado tal cual.** Va sólo el texto del posteo: nada de
encabezados, ni explicaciones, ni el pedido que te hicieron, ni separadores de
guiones.

**`notas.txt` no sale de acá.** Ahí van las decisiones que tomaste, lo que
asumiste y lo que propondrías para la próxima. La prueba: ¿lo leería un
paciente sin entender de qué estás hablando? Entonces va en `notas.txt`.

## Lo esencial de la marca

| | |
|---|---|
| Fondo | **blanco `#FFFFFF`** — es el 37,6% de una pieza medida |
| Tinta | `#181715` — titulares y barra de pie |
| Rojo | `#EB3141` — pantone 032, el acento |
| Gris | `#6D6E70` — 70% negro, primera línea de titular y metadatos |
| Gris claro | `#F0F0F0` — fondo de las piezas con recorte |
| Tipografía | Montserrat: 800/900 titulares, 700 subtítulos, 400/500 cuerpo |

**Esta marca vive en claro.** El rojo nunca es fondo: es siempre énfasis, y por
eso funciona. Una pieza con mucho rojo deja de parecer de esta clínica.

### La firma: el titular en dos colores

Es la regla que atraviesa todas las piezas publicadas. La primera parte va en
gris o tinta, y **la palabra que importa va en rojo**.

> MÁS CERCA TUYO → **CIUDAD DE LA COSTA**
> ¿Te toca el carné de salud? → **Ahora incluye hepatitis C.**

Por eso las plantillas toman `titulo` y `destacado` por separado. Si mandás todo
en `titulo`, la pieza sale de un solo color y deja de parecer de esta marca.

### El teléfono va SIEMPRE

Al revés que en otras marcas del sistema. Es una clínica sin agenda previa: el
WhatsApp no es un dato de más, es la conversión. La barra de pie con
**092 566 967** y **www.clinicapreventiva.com** se dibuja sola en `lateral` y
`tipografica`, y va en tira blanca en `sangre`.

## Las plantillas

### `lateral` — la de servicio
Foto a la izquierda, panel blanco a la derecha. Es la que usa la marca cuando
hay un **precio y una promesa de plazo**, que es su argumento más repetido.
```json
{"kicker":"EXAMEN PSICOTÉCNICO","titulo":"PSICOTÉCNICO","destacado":"EN 24 HORAS",
 "texto":"Para camioneros, choferes de ómnibus profesionales y gruistas.",
 "sello":"✓ Resultados garantizados en 24 hs","precio":"$6.100",
 "foto":"assets/x.jpg","foco":"50% 30%"}
```
`destacado` sale en un bloque rojo sólido. El titular se achica solo si es
largo, pero un titular de más de tres palabras va a salir chico igual.

### `sangre` — la de novedades
Foto a todo el cuadro, titular abajo sobre el degradé. Para cuando importa el
ambiente —la sala, el equipo, la sede— y no un precio. **Va en caja de oración,
no en mayúsculas.**
```json
{"kicker":"LO QUE AHORA PIDE EL MSP","titulo":"¿Te toca el carné de salud?",
 "destacado":"Ahora incluye hepatitis C.","texto":"...","foto":"...","foco":"50% 30%"}
```

### `recorte` — la más limpia
Persona a la izquierda sobre gris claro, titular a la derecha, fichas blancas
para los datos duros. La que mejor tolera texto largo.
```json
{"titulo":"MÁS CERCA TUYO","destacado":"CIUDAD DE LA COSTA","foto":"...","foco":"50% 22%",
 "fichas":[["Lunes a Viernes","de 7 a 18:45 hs."],["Sábados","de 8 a 11:15 hs."]],
 "pie1":"Ciudad de la Costa","pie2":"Costa Urbana Shopping"}
```

### Texto sobre foto: el rojo es el problema

**El rojo de esta marca contrasta mal contra casi cualquier foto.** Su
luminancia es media (0,202), así que su techo es 5,05:1 sobre negro PURO y
4,16:1 sobre blanco. Medido sobre tres stories que se publicaron:

| La palabra en rojo, sobre… | Contraste | Mínimo |
|---|---|---|
| El mostrador de la recepción | 1,72 : 1 | 3,0 : 1 |
| La cara de una persona | 1,43 : 1 | 3,0 : 1 |
| Una túnica blanca | **1,02 : 1** | 3,0 : 1 |

En la tercera la palabra tenía la misma luminancia que el fondo: no estaba.

**Ya está resuelto en el código y no hay que decidir nada.** Cuando hay foto,
`_plan()` la mide y decide: si el rojo llega, el destacado sale en rojo como
siempre; si no llega, **sale en un bloque rojo sólido con el texto en blanco**,
que da 4,16:1 sea cual sea la foto. La firma de la marca se conserva —la
palabra que importa sigue siendo la roja— sólo que el rojo pasa de tinta a
fondo.

Las otras dos reglas siguen valiendo:

- **Nada de texto CHICO en rojo sobre foto.** El mínimo para texto chico es
  4,5:1 y el rojo no llega nunca, ni en bloque. El kicker de `sangre` va en
  blanco con una barrita roja al lado.
- **El velo no es un valor fijo.** Se mide la foto en la franja donde va a
  caer el titular. Una cancha oscura pide 0,00; una sala de espera blanca pide
  0,46. Un valor fijo se rompe con la primera foto clara que suban.

Si agregás una plantilla con texto sobre foto, usá `_plan()` y `_titular()`.
No inventes un degradé a ojo ni elijas el color a ojo.

### El pie de contacto

Se dibuja solo con `_pie()` en `lateral`, `sangre` y `tipografica`. **Banda
blanca, línea fina de separación, íconos rojos chicos, texto en el gris de
marca y nada en negrita.**

Fue negro hasta el 3/8/2026, copiado de una pieza publicada. **El negro no es
un color de esta marca**: una barra oscura al pie de una pieza clara pesa más
que el contenido. Lo mismo pasó con el sello de garantía, que era una píldora
negra sólida y ahora es un contorno gris con el tilde en rojo.

Si aparece un elemento nuevo, la regla es: **blanco, gris y rojo. Nada de
negro sólido.**

### `tipografica` — sin foto
Sólo texto sobre blanco, con trama de puntos y barra roja al costado. Para
avisos, cambios de horario y datos de salud pública, donde una foto de banco no
aporta y encima ensucia.

### `rotulo` — el texto que va encima de un reel
Casi nunca se pide a mano: es la plantilla con la que el motor dibuja el
**rótulo de los reels**, y la declara `marca.py` en `PLANTILLA_ROTULO`. Sin
ella el motor busca una llamada `campana` —el nombre que tienen Boss y
Stadium—, no la encuentra, y frena el pedido antes de generar. Frenar está
bien, porque el rótulo se dibuja DESPUÉS de pagar el clip; lo que faltaba era
tener la propia.

Dos diferencias con `sangre`, y las dos salen de que abajo hay un video:

- **El destacado va en bloque rojo, no en texto rojo.** `sangre` mide la foto
  con `plan_titular` y recién ahí elige entre las dos versiones. Acá no hay
  nada que medir: el fondo cambia en cada cuadro.
- **No lleva la barra de contacto.** Es la única plantilla de esta marca sin
  ella. En una pieza fija el teléfono es la conversión —esta clínica no tiene
  agenda previa—, pero encima de un reel esa franja cae donde Instagram pone
  su propia interfaz. El número va en la placa de cierre.

## Carruseles y secuencias

Ver «Carruseles y secuencias» en la documentación del motor. Tipos de
diapositiva de ESTA marca:

| `tipo` | Campos | Para qué |
|---|---|---|
| `portada` | `kicker`, `titulo`, `destacado`, `bajada`, `foto`, `foco` | Siempre la primera |
| `punto` | `numero`, `detalle`, `titulo`, `texto` | **Un paso numerado.** Si el contenido es «1, 2, 3», es esta y no `cuadro` |
| `dato` | `kicker`, `cifra`, `titulo`, `texto` | **La más útil acá**: los argumentos de esta marca son casi todos numéricos |
| `texto` | `kicker`, `titulo`, `destacado`, `texto` | Respiro entre dos con foto |
| `cuadro` | `kicker`, `titulo`, `destacado`, `texto`, `cuerpo`, `responder` | Un cuadro suelto, sin número |
| `cierre` | `kicker`, `titulo`, `destacado`, `cta`, `tel` | Siempre la última |

### En una secuencia de stories se usan LOS MISMOS tipos

Hasta el 3/8/2026 el motor pasaba todas las diapositivas de una secuencia por
`cuadro` e ignoraba el `tipo` **en silencio**: quien pedía portada, tres puntos
y un cierre recibía cinco cuadros iguales y no se enteraba. Ya está arreglado.

Una secuencia de un proceso se arma así, y no con cinco `cuadro`:

```json
{"slides":[
 {"tipo":"portada","kicker":"FICHA MÉDICA","titulo":"Así es el proceso","destacado":"con nosotros.","bajada":"Tres pasos, un solo día."},
 {"tipo":"punto","numero":"01","detalle":"PRESENTATE","titulo":"Vení sin turno previo.","texto":"Acercate a cualquiera de nuestras dos sedes con los requisitos."},
 {"tipo":"punto","numero":"02","detalle":"ESTUDIOS","titulo":"Todo en una sola visita.","texto":"Examen médico, odontológico, laboratorio y examen visual."},
 {"tipo":"punto","numero":"03","detalle":"RETIRÁ","titulo":"Común o urgente.","texto":"En común lo retirás en días hábiles. En urgente, listo en 1 hora."},
 {"tipo":"cierre","titulo":"¿Te toca la ficha médica?","destacado":"Escribinos.","cta":"ESCRIBINOS POR WHATSAPP"}
]}
```

### La secuencia SIEMPRE termina en `cierre`

Es el único lugar donde alguien que miró toda la secuencia está dispuesto a
escribir. Si el pedido dice «3 stories» y el contenido son 3 pasos, hacé
**4**: los 3 pasos y el cierre. Decilo en `notas.txt`. Perder el cierre para
cumplir un número es perder la conversión de toda la pieza.

### El titular tiene que poder leerse solo

**El error más caro y el más fácil de cometer.** No partas una frase entre el
titular y el texto de apoyo:

> ✗ titulo: «NO NECESITÁS» · texto: «agendar hora. Acercate directamente…»

Entre una cosa y la otra hay 400 píxeles de blanco. El lector tiene que cruzar
ese vacío para completar una frase, y el apoyo arranca en minúscula. Se lee
como un error de maquetación, porque lo es.

> ✓ titulo: «Vení sin turno.» · destacado: «No hace falta agendar.»
> · texto: «Acercate a cualquiera de nuestras dos sedes con los requisitos.»

El titular es una idea cerrada. El apoyo la explica, y también empieza y
termina solo. **Nunca un titular que termine en dos puntos** colgando sobre el
vacío.

### Y `destacado` va siempre

Es la firma de la marca: la primera parte en tinta, la palabra que importa en
rojo. Si mandás todo en `titulo`, la pieza sale de un solo color y deja de
parecer de esta clínica. Una secuencia entera sin una sola palabra en rojo no
es de Clínica Preventiva.

`dato` es la que más rinde en esta marca: $1.600, 24 horas, 45 minutos, 14 años,
$6.100. Meter esas cifras en un titular común las desperdicia.

## Lo que dicen los números de la cuenta

Relevado el 2 de agosto de 2026 sobre @clinica.preventiva (4.573 seguidores):

| | |
|---|---|
| Reels, visualizaciones | 1.270 · 1.439 · 8.813 · **12.900** · **14.100** |
| Posteos de feed, likes | 4 · 9 · 19 · 24 |

**Dos reels superaron tres veces la cantidad de seguidores de la cuenta.** Los
338 posteos estáticos acumulados no llegan a 25 likes.

Consecuencia operativa: ante la duda entre una placa suelta y un carrusel o un
reel, **no es una placa suelta**. Si el pedido no especifica formato y el
contenido da para más de una idea, proponé el carrusel en `notas.txt`.

## Convenios con empresas — plantilla `convenio`

El cupón de un acuerdo: dos marcas arriba, un precio grande, y dónde canjearlo.
Es la única plantilla donde **entra un logo que no es el nuestro**.

```json
{"nombre":"convenio-santa-rosa","plantilla":"convenio","formato":"post",
 "data":{
   "titulo":"Convenio",
   "empresa":"Santa Rosa",
   "logo_socio":"assets/subidas/01-logo-santa-rosa.png",
   "servicio":"Carné de salud o deportivo",
   "condicion":"Presentando este cupón, todos los funcionarios de SANTA ROSA abonan:",
   "precio":"$U 800",
   "precio_pie":"IVA 10% y timbre profesional incluidos",
   "tel":"2200 8484",
   "whatsapp":"098 701 935",
   "sello":"Sin agenda previa",
   "sedes":[ ... ]}}
```

### El logo del socio

**Lo sube la persona.** Va a llegar en `assets/subidas/` como cualquier
adjunto: poné esa ruta en `logo_socio` y listo. La plantilla lo mete en una
caja de medida fija y lo achica hasta que entre — apaisado, cuadrado o
vertical, nunca se deforma. No le pongas ancho ni alto vos.

Tres cosas que sí tenés que mirar:

- **Si el logo es blanco o muy claro, no se va a ver**, porque el fondo de la
  pieza es blanco. Generá igual la pieza y pedí en `notas.txt` la versión
  oscura o a color del logo.
- **Si no subió ningún logo**, la pieza sale igual con el nuestro solo. Decilo
  en `notas.txt`: un convenio sin la marca del socio pierde la mitad de la
  gracia.
- **Nunca uses un logo bajado de internet.** Si la persona no lo subió, no lo
  busques: los logos tienen dueño y una versión vieja o de mala calidad en una
  pieza oficial es peor que no ponerlo.

### Reglas

- **El precio es el héroe.** Va adentro del contorno rojo y es lo más grande de
  la pieza. Si el convenio no tiene precio cerrado, esta plantilla no es la que
  va — usá `tipografica`.
- `condicion` es una frase, no un párrafo: **hasta 28 caracteres por línea** y
  tres líneas como máximo. «Presentando este cupón, todos los funcionarios de X
  abonan:» entra justo.
- **La foto va DE FONDO, a sangre, como en el resto de las piezas.** Poné
  `foto` y `foco` igual que en `sangre` o `lateral`. Si la persona eligió una
  del banco o subió una, **usala** — no la descartes por ser un cupón.
  Con foto, la plantilla sola: mide el velo que hace falta, pasa todo el texto
  a blanco y rellena la pastilla del precio. No toques colores ni tamaños.
- `sello` es opcional y va con el argumento más fuerte del convenio: «Sin
  agenda previa», «Resultados en 24 h».
- Los `sedes` van igual que en el resto — ver la sección de abajo.

## Las direcciones: usá el bloque `sedes`, nunca texto corrido

Cuando la pieza tiene que decir DÓNDE estamos, **no escribas las direcciones en
`texto`**. Hay un campo `sedes` que las dibuja con jerarquía: el nombre de la
sede como rótulo rojo chico, la dirección grande en tinta, y el horario en gris
y en dos líneas. Pegado en `texto` sale todo del mismo tamaño y no lo lee nadie
— ya pasó.

Copiá esto tal cual y sacá la sede que no corresponda:

```json
"sedes": [
  {"nombre": "Montevideo",
   "direccion": "Gral. Flores 3131 esq. Bvar. Artigas",
   "horario": "Lunes a viernes 7:00–16:45",
   "horario2": "Sábados 8:00–11:45"},
  {"nombre": "Ciudad de la Costa",
   "direccion": "Costa Urbana Shopping, Local 208",
   "horario": "Lunes a viernes 7:00–18:45",
   "horario2": "Sábados 8:00–11:45"}
]
```

Reglas:

- **`horario` y `horario2` son dos campos y no uno.** Entre semana y sábado son
  dos hechos distintos: en una sola línea con un `·` en el medio se leen como un
  bloque y se pierden los dos.
- Lo acepta `tipografica` (dos columnas sobre blanco), `sangre` (en tarjeta
  blanca sobre la foto) y `recorte` (alineado a la derecha). En `story` se
  apilan solas, no hace falta que hagas nada.
- **Si la persona eligió o subió una foto, la plantilla va con foto: `sangre`,
  no `tipografica`.** `sangre` dibuja las sedes en una tarjeta blanca apoyada
  sobre la imagen y queda perfecto. `tipografica` es para cuando NO hay foto.
  Elegir `tipografica` teniendo una foto elegida es descartarla en silencio.
- Con `sedes` puesto, **`texto` es opcional y casi siempre sobra**: el bloque ya
  dice todo. Un párrafo arriba de las direcciones compite con ellas.
- Si la pieza es de UNA sola sede, poné una sola en el array — y entonces **no
  repitas el nombre de esa sede en el `kicker`**, que queda dicho dos veces.
- En `post`, si la dirección es larga, cortala con `<br>` donde tenga sentido
  (`"Gral. Flores 3131<br>esq. Bvar. Artigas"`). En `story` no hace falta.

## Presentaciones en PDF

Formato **16:9 (1600 × 900)**. Se piden con `"plantilla": "presentacion"` y el
deck entero adentro de `data`:

```json
{"nombre":"servicios-empresas","plantilla":"presentacion",
 "data":{"acento":"rojo","fecha":"Agosto 2026",
   "pie":"clinicapreventiva.com · 092 566 967",
   "slides":[ ... ]}}
```

**No armes el PDF con el carrusel.** El carrusel es cuadrado y trae flechas
`> > >` e índice `01/08` de Instagram: adentro de un documento que nadie
desliza, eso queda como un error. Ya pasó — salió un deck con las diapositivas
cuadradas centradas y franjas blancas a los costados.

### Los ocho tipos de slide

| tipo | para qué | campos |
|---|---|---|
| `portada` | la primera | `kicker`, `titulo`, `bajada`, `foto`, `foco` |
| `seccion` | separador, en rojo pleno | `kicker`, `titulo`, `bajada` |
| `servicios` | **tarjetas en grilla** | `kicker`, `titulo`, `servicios[[titulo, detalle]]` |
| `contenido` | texto y bullets | `kicker`, `titulo`, `texto`, `puntos[]`, `foto`, `foco` |
| `datos` | cifras grandes | `kicker`, `titulo`, `datos[[numero, rotulo]]` |
| `tabla` | precios y plazos | `kicker`, `titulo`, `filas[[concepto, valor]]` |
| `foto` | imagen a sangre con tarjeta | `kicker`, `titulo`, `bajada`, `foto`, `foco` |
| `cierre` | el llamado a la acción | `titulo`, `telefono`, `lineas[]` |

### Reglas

- **Una lista de prestaciones va en `servicios`, no en una slide por servicio.**
  Seis servicios entran en una página como tarjetas y se comparan de un vistazo.
  Seis páginas con una foto de la sala de espera cada una son seis páginas medio
  vacías donde el que mira pierde el hilo. Con más de seis, partilo en dos
  slides de `servicios`.
- **`datos` y `tabla` son los que convencen.** «Desde 2011 · 2 sedes · 24h ·
  carné urgente en 1h» hace más por una propuesta que tres párrafos. Si el
  pedido no los trae, sacalos de la sección «Datos fijos» de este skill.
- **La foto es opcional en casi todo.** Esta marca tiene poco material y
  repetir la misma recepción en cinco páginas se nota. Mejor `servicios`,
  `datos` y `tabla`, que no llevan foto y se ven llenos.
- Un deck de propuesta bien armado son **6 a 9 páginas**: portada, sección,
  servicios, in company, datos, precios, cierre.
- La segunda columna de `tabla` se alinea sola a la derecha: poné ahí el precio
  o el plazo, y en la primera el concepto.

## El largo del titular en `sangre`

En `post` el titular va a 58px y entran **unos 22 caracteres por renglón**. Un
`destacado` de 35 caracteres ocupa dos renglones y deja la última palabra sola
—«sedes.» colgando— que es el error tipográfico más visible que existe.

Medí antes de escribir: `titulo` + `destacado` no deberían pasar de **tres
renglones en total**. «Te esperamos» + «en nuestras dos sedes.» entra en dos y
se lee de una. «en cualquiera de nuestras dos sedes.» no.

Y **el kicker no repite el titular**. «VENÍ CUANDO QUIERAS» arriba de «Te
esperamos» dice dos veces lo mismo con distinta letra. El kicker es para lo que
el titular NO dice: el servicio, la novedad, el plazo.

## Datos fijos

| Sede | Dirección | Horario |
|---|---|---|
| Montevideo (central) | Gral. Flores 3131 esq. Bvar. Artigas | L-V 7:00-16:45 · Sáb 8:00-11:45 |
| Ciudad de la Costa | Costa Urbana Shopping, Local 208 | L-V 7:00-18:45 · Sáb 8:00-11:45 |

Teléfono 2200 8484 · WhatsApp **092 566 967** · www.clinicapreventiva.com
Desde 2011 · Habilitada por el MSP · PREVECAL y One World Accuracy

**Servicios y precios:** carné de salud **$1.600** (urgente en 1 hora) ·
aptitud física **$1.600** · psicotécnico **$6.100** IVA incluido (24 horas) ·
análisis clínicos (24-48 h) · libreta de conducir (45 minutos) · medicina
laboral · convenios para empresas.

**Argumentos que la marca repite:** sin turno previo · resultados rápidos con
plazo explícito · precio final sin sorpresas · dos sedes · laboratorio propio.

**Alianzas:** Liga Universitaria de Deportes, Costa Urbana Shopping, MUFP.
La campaña **#PateadorDeLaFichaMédica** es la más grande y de ahí salen los
reels que funcionan.

## El banco de fotos: todavía no existe

`referencias/fotos.json` está vacío **a propósito**, y es la deuda más
importante de esta marca.

Las imágenes publicadas en Instagram no sirven como material: son piezas
terminadas, con el texto y el logo ya incrustados. Recortarles la foto da un
pedazo de baja resolución con elementos de la placa vieja adentro.

Mientras no haya banco:

- **Usá la foto que suba la persona.** Va a `assets/subidas/` y el prompt te la
  lista.
- Si no hay foto, usá `tipografica`, que está hecha justamente para eso. **No
  inventes una ruta de archivo** ni uses una foto de otra marca.
- Dejá escrito en `notas.txt` qué foto haría falta.

Lo que hace falta fotografiar: las dos recepciones, el laboratorio, el equipo
médico, una extracción, la fachada de cada sede. Con eso las piezas dejan de
parecer plantilla de banco de imágenes.

## Reels en video
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
| `club` | La menor, con palmas, 100 bpm | Clubes y deporte |
| `calmo` | Do mayor, sin palmas, 84 bpm | **El de esta marca.** Acompaña y no compite con una voz |
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

### Se valida antes de encodear

Un encode tarda minutos. Si un tramo pide un segundo que no existe, o el reel
se pasa de 90 segundos, el guion falla **antes**, con el motivo en castellano y
todos los problemas juntos. Los avisos con ⚠ no frenan nada, pero leelos: un
tramo de menos de 0,8 s no es un corte, es un parpadeo.

`velocidad` menor a 1 es cámara lenta. **Ese tramo va mudo a propósito** —el
audio estirado suena a dibujo animado—, así que no lo uses donde alguien habla.

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

- Poner el titular entero de un color: se pierde la firma de la marca.
- Usar el rojo como fondo de una pieza entera.
- Mayúsculas en `sangre` cuando el titular es una pregunta larga.
- Una foto de banco genérica cuando `tipografica` resolvía mejor.
- Sacar el teléfono. Acá va siempre.
- Publicar una placa suelta cuando el contenido daba para un carrusel.
