# El diseñador de cada cliente: qué se le puede pedir y qué no

Manual de uso del agente de diseño que corre a medida por cliente. Está escrito
para quien lo usa desde el chat, no para quien lo programa. Lo que dice acá está
verificado contra el motor: si algo figura como «no se puede», es porque se
probó y no funciona, no porque nos parezca.

Última revisión: 6/9/2026.

---

## 1 · Qué es esto

Cada cliente tiene **su propio diseñador**. No es una plantilla que se rellena:
es un agente que lee el manual de marca del cliente, elige la plantilla, escribe
el spec, **renderiza, mira el PNG que salió y lo corrige** antes de entregarlo.

Lo que hace que sea del cliente y no genérico son cuatro archivos suyos:

| | qué es |
|---|---|
| `marca.json` | los colores, las tipografías, los formatos, las paletas y las reglas que nadie puede pisar |
| `estilo.css` | cómo se ve cada cosa |
| `plantillas/` | los moldes de pieza que esa marca sabe hacer |
| el manual en Asistime | lo que el cliente escribe y edita él mismo — **manda sobre todo lo demás** |

Y el motor, que es el mismo para todos: mide contraste, encuadra fotos, corta el
texto que no entra y **avisa cuando algo salió mal**.

---

## 2 · Lo que SÍ se puede pedir

### Piezas

- **Una placa** — post cuadrado (1080×1080), vertical de feed (1080×1350) o
  story (1080×1920). Un pedido puede llevar varios formatos a la vez.
- **Un carrusel** — de 3 a 6 imágenes que se leen deslizando. Contá qué va en
  cada diapositiva, en orden.
- **Una secuencia** — 3 stories que se ven una atrás de otra.
- **Un PDF** — para lo que se manda por mail o se imprime.
- **Un video** (`crear_video`) — el archivo solo, sin texto encima.
- **Un reel** (`crear_reel`) — el video ya con título y música de la marca.
- **Editar videos que ya existen** (`montar_reel`) — unirlos, sacarles los
  tiempos muertos, subtitularlos. Esto no cuesta créditos.

### Sobre el contenido

- **Pedir el texto en tus palabras.** «Que diga que abrimos los domingos» sirve
  igual que darle el título escrito.
- **Mandar fotos.** Hasta 6 por pedido, hasta 12 MB cada una, en JPG o PNG. Se
  copian al momento, así que el link puede vencerse después sin problema.
- **Elegir una foto del banco por su nombre.** El banco es el conjunto de fotos
  del cliente, con su descripción y su encuadre ya guardados.
- **Pedir dónde va la foto.** «Que arranque desde abajo, sin espacio», «que se
  vea la cara», «centrada».
- **Pedir el clima.** «Que sea de impacto», «algo tranquilo», «que grite».
  El agente elige el fondo por eso, no por el nombre del color.
- **Un logo de un socio o convenio**, además del de la marca.

### Corregir lo que ya salió

**Ésta es la forma correcta de pedir un cambio:** decile qué querés distinto
sobre la pieza que ya te dio. El agente parte del diseño exacto y cambia SÓLO
eso — no lo rehace.

> «De la story que me pasaste, subí un poco el título y sacale el botón.»

Si en cambio volvés a describir la pieza entera, la va a hacer de nuevo desde
cero y va a salir distinta. **No es lo mismo corregir que volver a pedir.**

> ⚠ Al 6/9/2026 esto funciona en **Asistime**. En Boss, Stadium y Clínica
> Preventiva la corrección todavía rehace la pieza: falta desplegarles la
> función `api-disenos`. Está en la lista.

### Cambiar cómo trabaja

- **Editar el manual de marca desde Asistime.** Precios, tono, qué foto usar,
  qué no decir. El agente lo lee en cada pieza y **le gana al resto**.
- **Pedir una plantilla nueva** cuando falta un TIPO de pieza. Tarda unos cinco
  minutos y vuelve como borrador con su preview: no se usa hasta que alguien la
  publica.
- **Corregir una plantilla que ya existe**, sin reemplazarla por otra parecida.

---

## 3 · Lo que NO se puede pedir

Cada uno de estos se probó. No es que salga peor: **no sale.**

### Del diseño

- **«Poneme el texto acá exactamente, en este píxel».** El agente compone con
  las plantillas de la marca; no es un editor de posiciones. Lo que sí podés es
  pedir el efecto —«más aire arriba», «el título más grande»— y lo resuelve.
- **Un color que no es de la marca.** Está bloqueado a propósito. Si hace falta
  un color nuevo, va al `marca.json`, no al pedido.
- **Otra tipografía.** Misma razón.
- **Texto dibujado adentro de una forma.** Se rechaza: el texto lo pone la
  plantilla, porque sobre él corren las mediciones que evitan que se corte, que
  tape el logo o que quede ilegible. Un texto dibujado las apaga.
- **Emojis del sistema como si fueran un elemento de diseño.** Se ven distinto
  en cada teléfono y su color no es el de ninguna marca.
- **Una imagen traída de internet dentro de un retoque.** No se descarga nada de
  afuera al dibujar.
- **Que un dibujo tape el título o el logo.** Desde 25% de tapado la pieza no se
  entrega: hay que correrlo, achicarlo o mandarlo atrás.

### De las fotos

- **Una carpeta privada de Google Drive.** Si no está compartida como
  «cualquiera con el enlace», no la puede bajar nadie. Se comparte y se manda el
  mismo link — no hace falta descargar nada.
- **Un video disfrazado de foto**, o un archivo de más de 12 MB.
- **Más de 6 fotos en un pedido.** Seis es lo que entra en un carrusel.

### Del texto

- **Un título larguísimo.** Se achica hasta donde entra, y si aun así no entra,
  la pieza no sale: prefiere avisarte a entregarte una placa con el texto
  cortado. La salida es acortar.
- **Un dato sin fuente o un testimonio sin nombre**, en las marcas que lo tienen
  escrito en su manual. No es una preferencia del agente: es una regla del
  cliente.

### Del ritmo

- **Más de 20 pedidos por hora** por cliente.
- **Una respuesta instantánea.** Una placa tarda 2 a 4 minutos; un reel, más.
- **Que publique solo en Instagram sin que nadie lo mire.** Publicar es un paso
  aparte y explícito.

---

## 4 · Cómo pedir para que salga bien a la primera

1. **Decí para qué es la pieza, no cómo tiene que verse.** «Es un anuncio, tiene
   que frenar el pulgar» le dice más que «ponele fondo azul». El nombre de un
   color puede llevarlo al color equivocado; el propósito, no.
2. **Una idea por pieza.** Un título que dice dos cosas no se lee en el feed.
3. **Si mandás una foto, decí qué tiene que verse de ella.** «Que la jirafa
   arranque desde abajo, sin espacio» es una instrucción que el motor sabe
   ejecutar.
4. **Para cambiar algo, referite a la pieza que ya te dio.** No la vuelvas a
   describir entera.
5. **Si algo salió raro dos veces, no insistas con la misma frase.** Contá qué
   ves mal en la imagen: casi siempre es una pieza de plomería que falta, y con
   la descripción se encuentra.

---

## 5 · Qué mira el motor antes de entregarte una pieza

No reemplaza a alguien mirando el diseño. Lo que hace es que las fallas que se
miden con un número no lleguen al feed sin que nadie las nombre. Hoy son 17
mediciones. Las que más aparecen:

| mide | qué pasa si falla |
|---|---|
| que el texto entre en el lienzo | achica; si no entra ni al mínimo, **no entrega** |
| que un dibujo no tape el título ni el logo | avisa; **desde 25%, no entrega** |
| contraste del titular contra la foto | calcula el velo necesario y lo aplica |
| contraste de la firma contra lo que le quedó detrás | avisa con el número medido |
| que la firma no se apoye sobre el sujeto de la foto | acomoda la pieza sola |
| que la pieza no sea un rectángulo vacío | avisa |
| que un reel no salga mudo ni con negro en el medio | avisa |
| qué tapa Instagram arriba y abajo | avisa si algo cae ahí |

Todo eso se mide **sobre el PNG terminado**, no sobre la intención.

---

## 6 · Estado por cliente (6/9/2026)

| | Asistime | Boss Padel | Stadium | Clínica Preventiva |
|---|---|---|---|---|
| placas y carruseles | sí | sí | sí | sí |
| reels y video | sí | sí | sí | sí |
| publicar en Instagram | sí | sí | **no: sin cuenta cargada** | sí |
| banco de fotos | sí | sí | sí | sí |
| **corregir sin rehacer** | **sí** | falta desplegar | falta desplegar | falta desplegar |
| kit como datos (sin código) | sí | **no** | sí | **no** |
| paletas con su para-qué | 4 de 4 | — | 6 de 6 | — |

Las dos últimas filas son la misma deuda: Boss y Clínica todavía tienen su marca
escrita en Python, así que no pueden declarar paletas con su para-qué ni editarse
sin desplegar. Migrarlas es el trabajo de paridad que queda.
