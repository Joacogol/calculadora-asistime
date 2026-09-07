---
name: life-montevideo-disenos
description: Genera piezas de diseño para las redes de Life Montevideo (@lifemvd) — el club de Buceo de la familia Viví Life — con su identidad oficial: la pincelada LIFE, el frambuesa Pantone 7636 C (#BE3455) que es SUYO y no de los otros cuatro clubes, negro, blanco y una geométrica. Cinco plantillas: foto, titular, clase, plan y promo. Usar SIEMPRE que se pida una placa, story, reel o carrusel para Life Montevideo.
---

# Life Montevideo

Club de gimnasia, piscina y tenis en Buceo, Montevideo — Prof. Juan Carlos
Sabat Pebet 1240. Es **uno de los cinco clubes de Viví Life**: los otros son
Distrito M, Aguada, Zonamerica y el Outdoor Club. Su frase madre es «Una
comunidad que vibra».

## Lo primero, porque es lo que más se va a equivocar

| | |
|---|---|
| **El frambuesa es de ESTE club** | La familia comparte la pincelada LIFE, no el color: Montevideo es `#BE3455`, Aguada es rojo, Distrito M turquesa, Zonamerica verde y Outdoor lima. Usar el color de otro club en una pieza de éste es el error más visible que se puede cometer acá. |
| **El logo no se escribe, se pone** | «LIFE» es una pincelada dibujada, no una tipografía. No hay fuente que la imite y no hay que intentarlo: el logo va como logo, desde `assets/`. |
| **La grilla de clases no está en el manual** | Cambia todos los meses. Ningún día, hora, profesor ni cupo se completa sin que lo hayan dado. Una pieza vieja no es fuente. |
| **Los precios tampoco** | Ni de planes ni de promos. Si el pedido no los trae, la pieza sale sin precio, que es correcto. |

## La identidad, y de dónde salió cada parte

| | |
|---|---|
| **Frambuesa** | `#BE3455` — Pantone 7636 C, escrito en la «Guía de colores LIFE» oficial. Es exacto, no muestreado. |
| **Negro / tinta** | `#000000` y `#111111`. El manual usa Negro 6 C. |
| **Humo** | `#F4F4F4`, el blanco roto del propio manual. |
| **Los otros cuatro clubes** | Aguada `#D12421`, Distrito M `#00B5BD`, Zonamerica `#00C996`, Outdoor `#06F395`. Están en la paleta **para poder nombrarlos**, no para usarlos de acento. |
| **Logo** | Vectorizado del PNG oficial de `lifemontevideo.uy`. El PNG original quedó en `assets/` con el sufijo `-oficial` como testigo del trazado. |
| **Tipografía** | **Montserrat** (geométrica) y **Archivo** variable para la voz de póster. |

⚠️ **La tipografía es una aproximación, y conviene saberlo.** El manual usa
**Futura Condensed Extra Bold** en sus portadas. Futura es licenciada y no se
puede empaquetar; Montserrat es la geométrica libre más cercana, y Archivo en
su ancho angosto hace el papel de la condensada. En mayúsculas y a cuerpo
grande la diferencia no se lee. Si el club manda su Futura licenciada, se
cambian los archivos de `fonts/` y las tres voces siguen funcionando igual.

## Las tres voces tipográficas

| | Cuándo | Ejemplo |
|---|---|---|
| **`poster`** | titulares que gritan: promos, comunidad, campaña | «UNA COMUNIDAD QUE VIBRA» |
| **`normal`** | la voz de todos los días: una clase, un plan, un aviso | «PILATES REFORMER» |
| **`seca`** | rótulos y sobretítulos, mayúsculas muy espaciadas | «BODY & MIND», y el propio «MONTEVIDEO» del logotipo |

`seca` **nunca** es un titular. A cuerpo grande se desarma: está pensada para
la línea chica de arriba, que es exactamente el papel que cumple en el logo.

## Las cinco plantillas

| | Cuándo |
|---|---|
| **`foto`** | La que más se usa y la que menos hace. Gente entrenando, la sala, la piscina. **Sin texto encima**: el mensaje va en el epígrafe. |
| **`titular`** | Cuando el mensaje ES la pieza. Sobre foto o sobre color pleno. |
| **`clase`** | Una actividad con su día, su hora y su profesor. El pan de todos los días de un club. |
| **`plan`** | BASIC o ALL IN, con la lista de lo que incluye. |
| **`promo`** | Un descuento o una acción. La **única** donde el frambuesa es el fondo. |

## Las reglas que ya se sabían antes de la primera pieza

**El frambuesa no se lee como texto sobre una foto.** Es de luminancia media,
igual que el rojo de Clínica Preventiva, y ahí está medido: sobre una cara da
1,43:1 contra 3,0 de mínimo. Por eso `titular` y `clase` pasan el texto a
blanco solos cuando hay foto, y el color se queda para los fondos planos y para
los bloques sólidos, que es donde luce. **No lo fuerces con más velo:** si hay
que tapar la foto entera, no tenía sentido poner la foto.

**El día y la hora van en bloques, no en texto suelto.** Es el dato por el que
alguien guarda la pieza, y sobre una foto de sala —espejos, ventanas, paredes
blancas— un texto suelto se pierde en la peor mancha. Adentro de un bloque del
color del club, el blanco da 4,16:1 pase lo que pase debajo.

**La firma sobre el color del club va con el isotipo.** El lockup tiene
«MONTEVIDEO» en frambuesa escrito adentro del vector: sobre un fondo frambuesa
esa palabra desaparece y la pieza queda firmada a medias sin que nada falle.
Las plantillas lo cambian solas, pero si escribís una nueva, tenelo presente.

**Una cara generada no se publica.** Si el pedido manda una foto de un socio o
de un profesor, se usa. Inventar gente del club con `crear` no se hace: es un
problema distinto al de una pieza fea. `crear` sirve para lo que no tiene cara.

## Lo que todavía falta

- **El banco de fotos.** El club no mandó material, así que `referencias/` está
  vacío y la plantilla `foto` no se pudo previsualizar. Es el paso que más
  rinde de un alta —ver `motor/ALTA-DE-MARCA.md`, punto 3— y hay que hacerlo
  con las fotos reales, mirándolas, no leyendo los nombres de archivo.
- **La huella del motor.** `herramientas/verificar-motor.py --grabar` necesita
  al menos una foto en `assets/` para dibujar `foto`. Se graba cuando lleguen.
- **La música de los reels.** Sin banco propio todavía. Un club de gimnasia
  pide algo con pulso: house o pop electrónico de 120-128 BPM, sin voz.
- **El feed real.** El kit se armó con el manual de colores oficial y con
  `lifemontevideo.uy`. **Instagram no se pudo mirar** desde donde se armó esto.
  Igual que pasó con Stadium, es probable que mirar 24 posts reales corrija
  algo — cuánto se usa el color, cuánto texto lleva una pieza, si publican
  precios. Cuando se pueda ver, revisar este archivo.

## Dónde vive

Primer cliente **sin proyecto de Supabase propio**: sus tablas están en el
esquema `life_montevideo` del proyecto de la casa y sus archivos en el bucket
`disenos-life-montevideo`. Ver `alta/ESQUEMA-COMPARTIDO.md`. En Asistime es el
tenant **48**.
