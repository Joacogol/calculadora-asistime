---
name: larrique-disenos
description: Genera piezas de diseño para @larrique_uy, Larrique — la casa uruguaya de rulemanes, repuestos y lubricación con más de 50 años, para Automotriz, Industrial y Agrícola — con su sistema real: fondo azul noche, titulares condensados e itálicos en mayúsculas, foto de producto y de operación real, chips de beneficio con el anillo de la marca, co-branding con los 26 proveedores que representa y el pie de contacto siempre visible. Seis plantillas: producto, marca, servicio, dato, institucional y banner. Usar SIEMPRE que se pida una placa, story, estado de WhatsApp, carrusel, reel o banner de web / Mercado Libre para Larrique.
---

# Larrique

Casa uruguaya de rulemanes, repuestos y lubricación. Dos locales en Montevideo
—Casa Central en Galicia 1204 y División Industrial en Paraguay 2200—, ecommerce
propio con buscador por vehículo, tienda en Mercado Libre y envíos a todo el
país. Miembro de Groupauto Latam Austral. Tres unidades de negocio: **Automotriz,
Industrial y Agrícola**.

## Este kit se armó con manual, y por una vez eso alcanza

Con Life Montevideo el manual describía el logo y poco más, y el kit hubo que
sacarlo mirando el feed. Acá al revés: el **«Manual de Marca · Actualización
2026»** ya trae el sistema entero —fondo azul noche, jerarquías, fotografía,
co-branding, tono de voz, formatos por canal y hasta un checklist de nueve
preguntas— y el **«Sistema de contenidos digitales»** le agrega los nueve
pilares, la frecuencia y las medidas de cada pieza.

Lo que sí hubo que resolver es que **los dos manuales no dicen lo mismo**, y el
de 2026 explica por qué: conserva logo, colores y unidades del de 2025, y
actualiza todo lo demás.

| | Manual 2025 | Manual 2026 + piezas reales |
|---|---|---|
| **Fondo** | azul o verde plano a sangre | **azul noche `#071426`** o negro, casi siempre con foto |
| **Titular** | Dongle, redonda | **condensada, itálica, mayúsculas, enorme** |
| **Foto** | casi no hay | **producto real y operación real**: depósito, mostrador, campo |
| **Estructura** | libre | cinta con logo · badge · titular · bajada · chips · pie de contacto |
| **Proveedores** | nada | **co-branding**: su color como acento, nunca como sistema |

**La regla que resume todo: fondo oscuro, un titular que se lee en tres
segundos, el producto grande y de verdad, y el contacto siempre visible.** Un
fondo azul plano con una frase encima es una pieza del manual viejo.

## Los teléfonos del manual están mal, y esto importa

El manual 2026 trae piezas de ejemplo con **WhatsApp 092 340 500** y **teléfono
2902 1204**. Ninguno de los dos es de Larrique: son números de maqueta que
quedaron en los ejemplos. Los buenos, verificados en larrique.com.uy el
8/9/2026, son **092 580 580** y **2902 1773**, y son los que están escritos en el
pie de todas las plantillas.

Si alguna vez aparecen los otros en una pieza, salieron de copiar un ejemplo del
manual y hay que corregirlos.

## Las seis plantillas

| | Cuándo | Pilar del manual |
|---|---|---|
| **`producto`** | Una categoría o un producto con su marca. La de todos los días | 01, 09 · el 60% del feed |
| **`marca`** | El proveedor como protagonista: marca destacada de la semana, reingreso, alianza | 02 · los viernes |
| **`servicio`** | Envíos, cómo comprar, locales, horarios. **La única pieza clara** | 06 |
| **`dato`** | La que enseña: señales de cambio, diagnóstico, compatibilidad. Lleva lista | 03, 04 |
| **`institucional`** | La empresa: trayectoria, depósito, equipo, locales. La foto manda | 05, 08 |
| **`banner`** | Horizontal: `wide` 1920×704 de la web y `tira` 1500×250 de Mercado Libre | web / ML |
| **`rotulo`** | Casi nunca a mano: es el texto que el motor monta ENCIMA del video de un reel | reels |

`producto` tiene dos composiciones y son la misma pieza: `sobre_foto` para una
foto con fondo oscuro, y `diagonal` —el corte en dos con el producto sobre gris
claro— para las fotos de catálogo de proveedor, que vienen con fondo blanco.

## El acento dice de qué habla la pieza

No es una decisión de gusto y es lo más fácil de equivocar:

| | |
|---|---|
| **Azul Larrique** `#009BDB` | Automotriz, y todo lo que no sea claramente otra cosa |
| **Gris industrial** `#909090` | División Industrial: planta, mantenimiento, herramientas |
| **Verde agrícola** `#00B07A` | Campo: zafra, cosecha, maquinaria |
| **Naranja / amarillo** | **No son de Larrique.** Son los de Continental y Enerpac, y van sólo en una pieza de esa marca |

Un verde agrícola en una pieza de suspensión de auto es un error, y el checklist
del manual lo caza con su tercera pregunta: *¿el azul institucional está
presente?*

## El co-branding, que acá es la mitad del trabajo

`assets/marcas/` tiene **los 26 logotipos** de las marcas destacadas, bajados del
propio sitio de Larrique. El archivo se llama como la marca: `continental.png`,
`ntn.png`, `fag.png`.

Tres reglas, y las tres salen del manual:

1. **Larrique es el anfitrión.** El logo del proveedor identifica el producto,
   no la pieza.
2. **Un logo que no está en `assets/marcas/` no se dibuja.** No se saca de
   internet ni se redibuja: va el nombre en texto. El manual nombra además a
   Schaeffler, NKE, Koyo, GSP, Fied, BTE, A&S, Groz y Powerram — están en el
   catálogo pero no tienen archivo acá.
3. **Van sobre placa blanca.** Los 26 archivos son logotipos de imprenta —tinta
   oscura sobre transparente— y sobre el azul noche la mitad desaparece. Se
   midió con el de Continental. La alternativa sería pedirle a cada proveedor su
   versión en negativo; la placa es lo que se puede hacer sin inventarle a nadie
   un logo que no mandó.

## El primer formato apaisado del motor

`banner` sale en 1920×704 y en 1500×250, y hasta acá el motor sólo hacía piezas
verticales o cuadradas. No hizo falta tocarlo: el lienzo de esta marca mide
`width:100%` en vez de los 1080 fijos que escriben las demás, y el ancho lo pone
la ventana, que `render.py` ya abre con las medidas del formato. En vertical no
cambia nada — la ventana mide 1080 y el lienzo también.

## El rótulo de los reels es una plantilla, no un dibujo aparte

El texto que va encima del video —«ENVÍOS A TODO EL PAÍS» sobre el pasillo del
depósito— se dibuja con `rotulo`, que es una plantilla más del kit. Así, el día
que cambie la itálica de Larrique cambia también el rótulo de sus reels sin que
nadie se acuerde de venir a buscarlo.

Cuál es, lo declara la marca en `identidad.reel.plantilla`. **Sin eso el motor
busca una llamada `campana`** —el nombre que tienen Boss y Stadium— y frena el
pedido antes de generar: «esta marca no tiene la plantilla campana». Frenar es
lo correcto, porque el rótulo se dibuja DESPUÉS de pagar el video; lo que estaba
mal era no tener la propia. Con la plantilla puesta, el guardián devuelve vacío
y el pedido pasa.

Dos cosas que `rotulo` no hace y son a propósito: **no lleva el pie de contacto**
—esa franja cae justo donde Instagram pone su interfaz de reel— y **con
`sobre_video` no pinta ningún fondo**, sólo un degradado donde cae el texto. Un
velo entero taparía el video que se pagó, que es exactamente lo que le pasó a
Boss el 1/9/2026: ocho de diez segundos en negro.

## Las voces

| | |
|---|---|
| **`titulo`** | Archivo angosta, negra, **itálica**, mayúsculas. Todos los titulares |
| **`marca`** | La misma, un punto más ancha, para el nombre del proveedor en su color |
| **`numero`** | Ancha, negra y derecha, con cifras de ancho fijo: «+50», «25%» |
| **`bajada`** | Ancho normal, peso medio, caja baja. La única voz que no grita |
| **`seca`** | Mayúsculas muy espaciadas y chicas: badges, rótulos, el pie |

⚠️ **La itálica no es un adorno.** Es lo que el manual llama «diagonales /
movimiento», el mismo recurso que corta las piezas en dos. Un titular derecho
acá se ve de otra marca.

⚠️ **Dongle no está empaquetada.** El manual la conserva como tipografía
secundaria, pero ninguna pieza real la usa en un titular. Archivo tiene eje de
ancho y una itálica dibujada de verdad, así que las cinco voces salen de dos
archivos. Cuando una pieza institucional pida Dongle, se agrega.

## Lo demás que hay que saber

**El logotipo tiene exactamente dos versiones y por eso es un par de PNG y no un
vector pintable**: azul + negro sobre claro, todo blanco sobre oscuro. El motor
elige solo. El **símbolo** —los dos anillos— sí es un SVG y se pinta de
cualquier color: el manual lo autoriza como recurso gráfico, y de ahí sale la
viñeta de los chips y de las listas.

**El anillo del logo venía en `#00ADEF` y se repintó al `#009BDB` del manual.**
El PNG oficial trae un azul más claro que el que el manual declara; adyacentes,
la diferencia se ve.

**No hay iconos de terceros.** Un set descargado mete un tercer estilo de dibujo
en una identidad que tiene el suyo. Si algún día mandan su set, se dibuja adentro
del anillo y no cambia nada más.

**Ningún dato técnico se completa sin que lo hayan dado.** Ni un SKU, ni una
compatibilidad, ni un precio, ni un plazo de envío. Este rubro se equivoca caro:
una compatibilidad inventada es alguien que compra la pieza que no era. Y una
pieza vieja no es fuente — el stock y los precios cambian todas las semanas.

**Una foto de producto va sin filtro.** El manual lo pide con todas las letras:
la forma, la marca, el empaque y los detalles técnicos tienen que coincidir con
el producto real. Lo que se oscurece es la foto de contexto que hace de fondo.

**Ni `crear` ni `crear_video` dibujan productos.** Ninguna IA acierta un rulemán
NTN con su caja: sale el logotipo torcido y un número de parte inventado, y acá
un número de parte inventado es alguien que compra la pieza que no era. Los dos
sirven para lo mismo: una textura, un ambiente, el pasillo del depósito, un
camión saliendo, el taller — y siempre con la instrucción de no dibujar ningún
texto ni cartel. Para el producto está `montar_reel` con las fotos reales, que
además no gasta un crédito.

## Recortar el producto es el paso que más rinde

Las fotos de catálogo de proveedor llegan casi todas **sobre fondo blanco**, y la
composición `diagonal` de `producto` —el corte en dos con el repuesto sobre el
gris claro— está hecha para un producto **recortado**. El verbo `fondo` de
`editar_foto` es el puente entre las dos cosas: cuesta 3 créditos, tarda
segundos, y es el único que no redibuja un solo píxel del producto.

Los otros dos que este cliente va a usar todo el tiempo son `tamano` —una foto
de celular o de una web vieja— y `formato`, para llevar una horizontal a story
sin recortarle nada.

⚠️ **`retoque`, `escena` y `formato` REDIBUJAN parte de la imagen.** Sobre una
foto de contexto no hay problema; sobre un producto hay que mirar el resultado
contra el real antes de publicarlo. `fondo` y `tamano` no tienen ese riesgo.

**Y una foto de un sitio ajeno hay que copiarla antes de mandarla a Magnific.**
Magnific la baja por su cuenta, y contra una URL de otro dominio devuelve un
error suyo que no explica nada. Lo hace el worker solo desde el 8/9/2026 —ver
`fotero.copiar_entrante`— y de paso se presenta como un navegador: larrique.com.uy
le contestaba 403 al «Python-urllib» con el que `urlopen` se anuncia solo.

## Lo que todavía falta

- **El banco de fotos.** Larrique todavía no lo mandó; se irá agregando. Las
  seis plantillas se probaron con **dos imágenes sintéticas hechas con código**
  —manchas de color, no fotos— que sirvieron para ver estructura, cortes y
  legibilidad, y no quedaron en el repositorio. Catalogar el banco real es el
  paso que más rinde: ver `motor/ALTA-DE-MARCA.md`, punto 3.
- **La huella del motor.** `herramientas/verificar-motor.py --grabar` necesita al
  menos una foto en `assets/`. Se graba cuando lleguen las reales.
- **Publicar en Instagram.** Por ahora no: se prende cuando conecten la cuenta.
- **La música de los reels.** Sin banco propio, así que hoy salen mudos. Para
  este rubro pide algo con pulso y sin voz: electrónica industrial o rock
  instrumental de 110-125 BPM.
- **Dongle**, si aparece una pieza institucional que la pida.

## Dónde vive

Segundo cliente **sin proyecto de Supabase propio**: sus tablas están en el
esquema `larrique` del proyecto de la casa y sus archivos en el bucket
`disenos-larrique`. Ver `alta/ESQUEMA-COMPARTIDO.md`.

En Asistime es el tenant **80**, que ya tenía un agente de atención en
producción. El diseñador es el agente **605**, creado el 8/9/2026 sin pipeline
por pedido de Joaquín. Tiene su prompt, los dos documentos —reglas de marca y
catálogo de plantillas— y seis herramientas: `crear_diseno`, `estado_diseno`,
`corregir_diseno`, `montar_reel`, `crear_video`, `estado_reel`, `editar_foto` y
`estado_foto`. Ver `tools-asistime/LEEME.md`.

## Encuadre automático de productos

En `producto` diagonal, el motor mide la silueta visible (alfa), mantiene proporciones y encaja el producto entre encabezado, diagonal y pie. No usar `foco_producto` ni retoques CSS para empujarlo hacia abajo. Si `editar_foto` ya quitó el fondo, usar su URL resultante como foto del diseño, no el original blanco. Las fotos opacas se preservan completas: el motor no identifica ni borra fondos por color. Revisar la pieza; este cálculo protege la geometría, no garantiza una composición perfecta para cualquier foto.

## Fidelidad del brief

No rellenar chips con beneficios inventados. Marca no confirmada implica `marca` y `logos` vacíos. Copiar los dos precios y mostrar el porcentaje solicitado en la imagen. Usar el recorte acordado y conservar su transparencia. Acortar texto redundante antes de reducir al producto. Las prioridades operativas se cargan también desde `marca.json` en cada pedido.
