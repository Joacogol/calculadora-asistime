---
name: stadium-disenos
description: Genera piezas de diseño para las redes de Stadium — la cadena uruguaya de 34 tiendas deportivas fundada en 1977 — con su identidad real, sacada de su feed y no del logo: producto sin texto encima, campañas con paleta y tipografía propias, gente del equipo con su nombre, y el naranja reservado para las promos. Cinco plantillas: producto, campana, equipo, promo y precio. Usar SIEMPRE que se pida una placa, story, reel o carrusel para Stadium o @stadium_uruguay.
---

# Stadium

Cadena uruguaya de tiendas deportivas. **34 locales** y venta online desde
2006. Vende marcas de terceros —adidas, Nike, Puma, New Balance, Converse,
Umbro, Topper— para mujer, hombre y niños.

## Lo primero, porque es lo que más se equivoca

Este kit se armó dos veces. La primera, mirando el sitio y el logo. La
segunda, mirando **24 posts reales del feed**. Las tres cosas que cambiaron son
las tres que hay que tener presentes:

| | |
|---|---|
| **El naranja casi no se usa** | Aparece en **1 de 24** posts. La grilla es beige, tan, kraft, gris, marrón y blanco. El naranja es del logo y de las promos, no de todas las piezas. |
| **Más de la mitad no tiene texto** | Fotos de producto y punto. El mensaje va en el epígrafe. Por eso `producto` es la plantilla más usada y la que menos hace. |
| **No hay precios en la imagen** | Cero en 24. El precio va en el epígrafe. `precio` existe para excepciones. |

Y la cuarta, que es la estructural: **cada campaña trae su propia identidad y
mientras dura, manda ella.**

## La identidad, y de dónde salió cada parte

| | |
|---|---|
| **Naranja** | `#FF6600` — escrito en el `logo.svg` oficial como `fill:#f60`. Es exacto. |
| **Tinta** | `#222222` · **Grises** `#999999` y `#E1E3E4` |
| **Tipografía** | **Archivo** variable. Tiene eje de ancho (62→125), así que la condensada de póster de las campañas sale del mismo archivo. |
| **Serif** | **Playfair Display**, para las campañas aspiracionales. Es la voz de «Para la N°1 de mi equipo». |
| **Logo** | el vectorial oficial. La **S** del isotipo se extrajo de su propio trazo. |

**Ojo con el naranja.** El sitio usa `#EF6A00` para su interfaz. Se resolvió a
favor del logo, que es la especificación de la marca.

Stadium nombró Helvetica Neue y Gotham: las dos son licenciadas y no se pueden
empaquetar. Archivo es la misma familia visual que el logotipo y viene libre.

⚠️ **Los colores de las campañas (`papa`, `madre`) están sacados a ojo de
capturas del feed, no de un manual.** Sirven para que una pieza salga parecida.
Cuando Stadium mande la campaña con sus valores, se corrigen en `brand.py` y
quedan bien para siempre.

## Las tres voces tipográficas

| | Cuándo | Ejemplo real |
|---|---|---|
| **`cond`** | campañas de volumen y precio | «CON PAPÁ SIEMPRE HAY EQUIPO» |
| **`serif`** | aspiracional, femenino, Día de la Madre | «Para la N°1 de mi equipo» |
| **`normal`** | cuando la campaña no tiene identidad propia | la voz neutra de la marca |

## Las cinco plantillas

| | Cuándo | El protagonista |
|---|---|---|
| **`producto`** | una foto de producto, sin más | la foto |
| **`campana`** | una campaña con nombre | el título, en la paleta de la campaña |
| **`equipo`** | alguien de la casa | la persona, con su nombre y su área |
| **`promo`** | sorteo, descuento, acción con socios | la mecánica |
| **`precio`** | excepción: una placa con precio | el precio |

Las cinco son **datos**, no código: se corrigen desde el chat sin desplegar
nada. No hay ninguna sobre la que haya que contestar «esa necesita código».

### Lo que cada una resuelve, y por qué así

**`producto`** — parece que no hace nada y es la más usada. Aporta el encuadre
al formato y el foco, nada más. `nombre` y `firma` vienen vacíos/apagados **a
propósito**: en el feed real estas piezas no llevan texto ni logo.

**`campana`** — acá la campaña pisa a la marca. La paleta entra por `estilo` y
se puede corregir campo por campo. Tres decisiones que vienen del feed:

- **Sobre foto el título va BLANCO**, aunque la paleta diga otra cosa. Es lo
  que hace la marca, y además es lo único que se lee: el celeste de Día del
  Padre sobre una foto de catálogo en blanco no llega a contraste ni con el
  velo al máximo, y la pieza sale gris.
- **El salto de línea se respeta.** En las piezas reales el corte no cae donde
  quiera el navegador: «CON PAPÁ / SIEMPRE HAY / EQUIPO».
- **Sin foto la pieza se centra sola.** `arriba` existe para dejarle lugar al
  producto o la persona; sin ninguno de los dos, deja media pieza vacía.

**`equipo`** — el formato propio de Stadium: los protagonistas de la campaña de
Día del Padre son sus empleados, cada uno con su nombre y su área. **La chapita
es lo que hace la pieza**; sin ella es un retrato cualquiera. El título va en
una esquina **que se elige**, porque la que sirve depende de dónde quedó la
cabeza en esa foto.

**`promo`** — la única donde el naranja es el fondo, y la única con la letra
chica **obligatoria en el contrato**. Una promo sin condiciones escritas se
discute en la caja de una tienda. Si lleva foto, tiene que ser un **recorte con
fondo transparente**: una de catálogo con fondo blanco se ve como un rectángulo
pegado encima del naranja.

**`precio`** — se deja porque una placa de Precios de Locos la va a necesitar,
pero no es el camino normal. Antes de usarla, confirmá que quieren el precio en
la imagen.

## Reglas que valen más que el diseño

1. **Ningún precio, porcentaje ni fecha que no hayan dado.** Y una pieza vieja
   **no es fuente**: en retail los precios cambian todas las semanas.
2. **Si el precio tiene una condición, la condición va en la pieza.**
3. **El logo de un tercero se usa sólo si Stadium lo mandó.** No se saca de
   internet ni se redibuja, y nunca se deforma: va siempre encajado en una caja
   con `contain`.
4. **En la pieza va la web, no el teléfono.**
5. **Los nombres de las personas son de personas reales.** Si no estás seguro
   de cómo se escribe, preguntá antes de publicar.

## Lo que todavía no tiene

**Carruseles y PDFs** (`DIAPOS` y `PRESENTACION`). Para una cadena de retail el
carrusel de varios productos es una pieza obvia y va a hacer falta. Se dejó
afuera a propósito: el motor falla fuerte y con nombre y apellido si alguien
pide un carrusel, que es mejor que un carrusel que sale mal.

**Reels hablados con subtítulos.** Stadium los hace —hay varios en el feed, con
los subtítulos quemados— y el motor hoy sólo arma reels de rótulos sobre
imagen. Existe un pack de edición de reels hablados que resuelve justo eso.

## Una advertencia sobre la verificación

Boss y Clínica tienen una red que Stadium no: sus plantillas ya existían, así
que un cambio se prueba dibujando todo y comparando byte a byte contra antes.
Acá no hay «antes» — esta versión se verificó **mirando** los previews en post
y story, con el juego normal y con el límite, y corrigiendo lo que se veía mal.
Así se encontraron cuatro cosas: el subrayado atado al cuerpo de letra en vez
de al ancho del título, el vacío de media pieza sin foto, el `flex:1` que
anulaba el centrado, y las cifras de estilo antiguo de la serif.

Desde el despliegue siguiente sí aplica la regla dura:

```bash
python3 herramientas/verificar-motor.py stadium-disenos --grabar    # ANTES
python3 herramientas/verificar-motor.py stadium-disenos --comparar  # DESPUÉS
```
