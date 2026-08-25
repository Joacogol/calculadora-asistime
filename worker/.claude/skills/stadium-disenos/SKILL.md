---
name: stadium-disenos
description: Genera piezas de diseño para las redes de Stadium — la cadena uruguaya de 34 tiendas deportivas fundada en 1977 — con su identidad real: el naranja #FF6600 del logotipo oficial, Archivo como única tipografía, la barra de pie con stadium.com.uy y cuatro plantillas de retail (precio, sale, lanzamiento, marca). Usar SIEMPRE que se pida una placa, story, reel o carrusel para Stadium o @stadium.uy — una oferta, un lanzamiento, una campaña de descuento o una acción con adidas, Nike, Umbro o Topper.
---

# Stadium

Cadena uruguaya de tiendas deportivas. **34 locales** en todo el país y venta
online desde 2006. Vende marcas de terceros —adidas, Nike, Umbro, Topper,
Converse— para mujer, hombre y niños.

Lo que la separa de las otras marcas del motor: acá se comunica **producto,
precio y campaña**, no servicios ni sedes. El precio es el protagonista y la
letra chica no es un detalle legal, es parte del mensaje.

## La identidad, y de dónde salió

| | |
|---|---|
| **Naranja** | `#FF6600` — está escrito en el `logo.svg` oficial como `fill:#f60`, y el favicon (la S blanca sobre naranja) lo confirma |
| **Tinta** | `#222222` |
| **Grises** | `#999999` metadatos y precio tachado · `#E1E3E4` fondos y separadores |
| **Tipografía** | **Archivo** variable, sola. El logotipo es un grotesco denso de la familia de Helvetica, y Archivo es exactamente eso |
| **Logo** | el vectorial oficial, bajado de stadium.com.uy. La **S** del isotipo se extrajo del propio trazo del logotipo |

**Ojo con el naranja.** El sitio usa `#EF6A00` para su interfaz — más apagado.
Se resolvió a favor del logo, que es la especificación de la marca y no una
decisión de un tema de e-commerce.

Sobre las tipografías: Stadium nombró Helvetica Neue y Gotham. Las dos son
licenciadas y no se pueden empaquetar. Se evaluó imitar la geométrica tipo
Gotham y **no conviene**: el logo no es geométrico, así que una geométrica al
lado se lee como un segundo sistema. Archivo es la misma familia visual que el
logotipo y viene libre. Si Stadium pasa las licencias, se cambia en una línea
de `brand.py`.

## Las cuatro plantillas

| | Cuándo | El protagonista |
|---|---|---|
| **`precio`** | un producto con su precio | el precio |
| **`sale`** | una campaña de descuento, sin producto | el porcentaje |
| **`lanzamiento`** | una colección o modelo nuevo | la foto |
| **`marca`** | campaña de una marca de tercero | su logo |

Las cuatro son **datos**, no código: se pueden corregir desde el chat sin
desplegar nada. No hay ninguna sobre la que haya que contestar «esa necesita
código».

### Lo que cada una resuelve, y por qué así

**`precio`** — la foto tiene **altura propia**, no lo que sobra. Con `flex:1`
un nombre de producto de dos líneas le comía la mitad y el producto quedaba de
estampilla. El nombre baja de cuerpo en dos escalones (34 y 58 caracteres) en
vez de achicar la foto.

**`sale`** — la única que invierte el fondo: naranja pleno, logo en blanco. La
S del isotipo va gigante y al 10% de opacidad como textura, para no agregar un
elemento que la marca no tenga.

**`lanzamiento`** — el velo sobre la foto **se mide**. `plan_titular` calcula
la opacidad mínima para que el texto blanco llegue a 4,5:1 sobre esa foto en
particular. Un valor fijo se rompe con la primera foto que no se parezca a la
que se usó para calibrarlo.

**`marca`** — la única donde entra una marca que no es Stadium. El logo del
socio **no se dibuja, se encaja**: caja de medida fija, `object-fit: contain`,
sobre tarjeta blanca. Nunca se deforma y siempre se ve, sin saber de qué color
viene. Un logo de adidas estirado es la forma más rápida de perder el acuerdo.

## Reglas que valen más que el diseño

1. **Ningún precio, porcentaje ni fecha que no hayan dado.** Una placa con un
   precio que no es termina en un reclamo en la caja de una tienda. Y una pieza
   vieja **no es fuente**: en retail los precios cambian todas las semanas.
2. **Si el precio tiene una condición, la condición va en la pieza.** «Hasta
   agotar stock», «no acumulable», «válido hasta el…».
3. **El logo de una marca de tercero se usa sólo si Stadium lo mandó.** No se
   saca de internet ni se redibuja. Si nombran la marca pero no mandan el logo,
   se escribe el nombre en texto — el campo `marca` de `precio` es para eso.
4. **En la pieza va la web, no el teléfono.** El llamado a la acción es
   `stadium.com.uy` y ya está en la barra de pie. El teléfono es de atención al
   cliente, no de venta.

## Lo que todavía no tiene

**Carruseles y PDFs** (`DIAPOS` y `PRESENTACION`). Para una cadena de retail el
carrusel de varios productos es una pieza obvia y va a hacer falta. Se dejó
afuera a propósito en vez de armarlo a medias: el motor falla fuerte y con
nombre y apellido si alguien pide un carrusel, que es mejor que un carrusel que
sale mal.

## Una advertencia sobre la verificación

Boss y Clínica tienen una red que Stadium no: sus plantillas ya existían, así
que un cambio se puede probar dibujando todo y comparando byte a byte contra
antes. Acá no hay «antes» — la verificación de esta primera versión fue mirar
los previews en los cuatro formatos, con el juego normal y con el límite.

Desde el despliegue siguiente sí aplica la regla dura:

```bash
python3 herramientas/verificar-motor.py stadium-disenos --grabar    # ANTES
python3 herramientas/verificar-motor.py stadium-disenos --comparar  # DESPUÉS
```
