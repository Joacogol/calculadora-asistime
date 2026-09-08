---
name: life-montevideo-disenos
description: Genera piezas de diseño para @lifemvd, Life Montevideo — el club de Buceo de la familia Viví Life — copiando la estética real de su feed: fotos tratadas en blanco y negro o barridas, frases apiladas en mayúsculas con palabras en el color del club, el #VIVÍLIFE cruzando la foto, números gigantes para los eventos. Todo vertical, nada de fondos planos. Cinco plantillas: foto, manifiesto, evento, clase y aviso. Usar SIEMPRE que se pida una placa, story, reel o carrusel para Life Montevideo.
---

# Life Montevideo

Club de gimnasia, piscina y tenis en Buceo — Prof. Juan Carlos Sabat Pebet
1240. Uno de los cinco de Viví Life: los otros son Distrito M, Aguada,
Zonamerica y el Outdoor Club. Su frase madre es «Una comunidad que vibra».

## Este kit se armó dos veces, y la segunda cambió casi todo

La primera vez, con el manual de colores oficial y el sitio. La segunda,
mirando **cinco piezas reales del feed**. Lo que cambió no fue un detalle:

| | Lo que decía el manual | Lo que hace el feed |
|---|---|---|
| **Las fotos** | nada | **ninguna sale cruda**: blanco y negro con grano, barridas, oscurecidas |
| **El color como texto** | nada | **sí va**, encima de esas fotos, y funciona por el tratamiento |
| **El `#VIVÍLIFE`** | un lockup en una página | **cruza la foto** como marca de agua: es la firma de la cuenta |
| **Los otros colores** | uno por club | **celeste para la piscina, verde para hybrid**: el acento es la actividad |
| **El formato** | nada | **todo vertical**, 9:16 |
| **Fondos planos** | el color a sangre parecía obvio | **cero**. Ni una pieza |
| **Sponsors** | nada | co-marca «PUMA × #VIVÍLIFE» |

**La regla que resume todo: acá la pieza es una foto tratada con texto encima.**
Un fondo de color liso con un titular es una pieza de otra marca.

## Por qué el tratamiento de la foto es lo primero que se elige

No es un filtro de gusto. Es lo que hace posible el resto: sobre una foto **sin
color propio**, el frambuesa escrito encima queda como lo único vivo de la
pieza; sobre una foto en color compite con todo y la pieza se ensucia. Por eso
el campo `tratamiento` viene primero en todas las plantillas.

| | |
|---|---|
| `bn` | blanco y negro, contraste subido, grano. El de la pieza de la corredora |
| `oscuro` | baja la luz y deja el color. El de la cancha de noche |
| `barrido` | desenfoca y oscurece: la foto es textura debajo de un número |
| `natural` | existe para una excepción, no para el día a día |

## El acento aguanta como texto GRANDE, no como rótulo chico

Se midió acá mismo. «VIBRAR FUERTE» en frambuesa a 132 px sobre una foto
tratada se lee perfecto. «BODY & MIND» en el mismo frambuesa a 25 px y con
mucho interletrado, sobre la misma foto, **no se lee**: un trazo finito de un
color de luminancia media sobre negro desaparece.

Por eso las plantillas ponen los rótulos en blanco cuando hay foto, y dejan el
acento para lo que ocupa media pieza. No es «el acento no va sobre foto» —eso
sería falso y contradiría el feed—: es que el acento necesita cuerpo.

## Las plantillas

| | Cuándo |
|---|---|
| **`foto`** | La foto tratada con la marca encima: el `#VIVÍLIFE` cruzándola, o el logotipo gigante. A lo sumo una línea baja en minúsculas. Sin titular |
| **`manifiesto`** | La pieza firma de la cuenta: una frase apilada sobre blanco y negro, con algunas líneas en el color del club |
| **`evento`** | Un número o una fecha gigante: «60 min NADO», «SAB. 12.09». También la que lleva sponsor |
| **`clase`** | Una actividad con su horario y su profesor |
| **`aviso`** | Un plan, una promo, un cambio: titular, lista y letra chica |
| **`rotulo`** | Casi nunca a mano: es el texto que el motor monta ENCIMA del video de un reel |

`aviso` reemplaza a las dos que había antes —una de planes y una de promos—
porque las dos estaban armadas sobre un fondo de color a sangre, y de eso no
hay nada en esta cuenta. Un plan y una promo son la misma pieza: un titular,
una lista y la letra chica.

## Cómo se marcan las palabras en color

En `manifiesto`, con un **asterisco al principio de la línea**:

```
*VIBRAR FUERTE
*TAMBIÉN
ES
CONECTAR
```

Un marcador de un carácter es lo único que sobrevive a que la frase se escriba
en un chat. Una lista aparte de «qué líneas van en color» se desincroniza a la
primera corrección.

Y una palabra de tres letras o menos —ES, Y, DE— **sale más chica sola**. El
«ES» de la pieza real no es un descuido: una conjunción al mismo cuerpo que el
titular rompe el ritmo de la pila.

## Las voces

| | Cuándo |
|---|---|
| **`titulo`** | Archivo angosta, mayúsculas, líneas casi pegadas. Casi todas las piezas |
| **`poster`** | La misma pero más angosta, para una frase larga que igual tiene que gritar |
| **`numero`** | Los números gigantes: el «60» del nado, el «12.09» del hybrid |
| **`susurro`** | Minúsculas, chica: «sos mucho más que eso». **Nunca en mayúsculas ni grande** |
| **`seca`** | Mayúsculas muy espaciadas, como el «MONTEVIDEO» del logo. Rótulos, nunca un titular |

⚠️ **La tipografía es una aproximación.** El manual usa **Futura Condensed
Extra Bold**, que es licenciada y no se puede empaquetar. Archivo es un
grotesco con eje de ancho, así que las tres voces de display salen del mismo
archivo y en mayúsculas a cuerpo grande la diferencia no se lee. Si el club
manda su Futura, se cambian los archivos de `fonts/` y todo sigue igual.

## Los colores

| | |
|---|---|
| **Frambuesa** `#BE3455` | Pantone 7636 C. El del club. Va cuando no hay razón para otro |
| **Celeste** `#37C6E8` | Piscina: nado, hidro, aqua. Muestreado de una pieza, no del manual |
| **Verde** `#06F395` | Hybrid, outdoor y lo que lleve sponsor deportivo |
| **Negro / blanco** | Negro 6 C. El feed es oscuro |

Los otros clubes —Aguada `#D12421`, Distrito M `#00B5BD`, Zonamerica
`#00C996`— están en la paleta para poder nombrarlos en una pieza de la familia.
Un rojo Aguada en una pieza de Montevideo que no habla de Aguada es un error.

## Lo demás que ya se sabía

**El logo no se escribe, se pone.** «LIFE» es una pincelada dibujada. No hay
fuente que la imite y no hay que intentarlo.

**Una pieza se firma UNA vez.** O el `#VIVÍLIFE` grande, o el logotipo, o nada.
Nunca dos. En el feed, la marca de agua firma las piezas de clima y de
comunidad; el logotipo grande, las que presentan el club; las de evento no
llevan ninguno porque ya llevan la co-marca del sponsor.

**Sobre el color del club, la firma va con el isotipo.** El lockup lleva
«MONTEVIDEO» en frambuesa escrito adentro del vector: sobre un fondo frambuesa
esa palabra desaparece y la pieza queda firmada a medias sin que nada falle.

**No hay pastillas ni iconos.** En el feed no hay uno solo. Lo que separa un
dato del otro es el tamaño de la letra y, cuando hace falta subrayar, el trazo
a pincel del propio logotipo. Una pastilla redondeada en una identidad de
pinceladas y mayúsculas se ve prestada de otra marca.

**La grilla de clases y los precios no están en el manual.** Cambian. Ningún
día, hora, profesor, cupo ni precio se completa sin que lo hayan dado. Una
pieza vieja no es fuente.

**Una cara generada no se publica.** Si mandan la foto de un socio o un
profesor, se usa. Inventar gente del club con `crear` no se hace.

**El logo de un sponsor va sólo si lo mandaron.** No se saca de internet ni se
redibuja. Si no lo mandaron, va el nombre en texto, que es lo que `evento`
permite.

## Lo que todavía falta

- **El banco de fotos.** El club no mandó material. Las piezas se probaron con
  **dos fotos sintéticas hechas con código** —manchas de color, no fotos— que
  sirvieron para ver estructura, tratamiento y grano, y no están en el
  repositorio. Catalogar el banco real es el paso que más rinde de un alta: ver
  `motor/ALTA-DE-MARCA.md`, punto 3.
- **La huella del motor.** `herramientas/verificar-motor.py --grabar` necesita
  al menos una foto en `assets/`. Se graba cuando lleguen las reales.
- **La música de los reels.** Sin banco propio. Un club así pide algo con
  pulso: house o pop electrónico de 120-128 BPM, sin voz.
- **Más feed.** Se miraron cinco piezas. Con Stadium hicieron falta 24 para que
  aparecieran los patrones que no se ven en una muestra chica.

## Dónde vive

Primer cliente **sin proyecto de Supabase propio**: sus tablas están en el
esquema `life_montevideo` del proyecto de la casa y sus archivos en el bucket
`disenos-life-montevideo`. Ver `alta/ESQUEMA-COMPARTIDO.md`.

No está en el secreto `clientes-registro` y no hace falta que esté: el worker
lo lee de `public.clientes` en cada corrida y le presta la URL y la clave de la
casa, que son las suyas. Un cliente de esquema compartido no tiene ninguna
clave propia.

En Asistime es el tenant **48**, que ya existía con dos agentes de atención en
producción; el diseñador es el agente **604**, aparte, con doce herramientas
escritas para este club. Ver `tools-asistime/LEEME.md`.
