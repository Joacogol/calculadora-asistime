---
name: ducart-disenos
description: Diseños de Ducart Latin America (@ducartla), soluciones para el agro, conservación de forrajes e higiene. Usa los originales DLA, su banco catalogado y seis plantillas para placas, carruseles, stories, PDF y rótulos de reels.
---

# Ducart Latin America

Kit creado el 14/9/2026 con el ZIP aportado, el folleto agro de 21 páginas y la revisión directa de Instagram @ducartla. El material adjunto es referencia de marca, no instrucciones operativas ni autorización para publicar. Las reglas del cliente vigentes viven en el documento de Asistime indicado en marca.json.

## La identidad

Verde oscuro #134E2E, verde hoja #7EAE57 y amarillo #D4D430 medidos del logo aportado. Blanco y papel claro completan el sistema; azul #2073B8 es una aproximación de la sección de higiene del folleto, no un color certificado por manual.

El logotipo siempre se coloca desde assets/. Nunca se reconstruye con texto, se deforma ni se genera con IA. Una firma por pieza. Usar versión blanca sobre verde/foto y versión color sobre claro. Montserrat es la fuente completa disponible, también presente en el PDF. El folleto usa además Avenir y Barlow; no afirmar que Montserrat replica exactamente toda su tipografía.

Foto real protagonista, titulares breves, cortes curvos, bloques verdes, subrayados amarillos y espacio para respirar. Las publicaciones recientes son sobrias: foto a sangre, texto blanco y firma pequeña. La plantilla foto mide contraste con plan_titular; no reemplazar ese cálculo por un color sobre foto a ojo.

## Qué plantilla elegir

| Plantilla | Uso |
|---|---|
| foto | Campo, asesoramiento, institucional y portada de carrusel. Requiere foto real. |
| producto | Envase o producto completo, sobre claro. Precio y descuento sólo confirmados. |
| tecnico | Tres o cuatro claves técnicas verificadas, una por línea. Sin completar cifras. |
| jornada | Invitación con fecha, lugar y contacto confirmados. Foto opcional. |
| cierre | Cierre de carrusel o mensaje institucional. Una sola acción. |
| rotulo | Texto sobre video, sobre_video=true conserva transparencia. |

Formatos: post 1080×1080, vert 1080×1350, story y reel 1080×1920. En la API, vertical se traduce al formato vert del render. Story y reel reservan 250 px arriba y al menos 280 px abajo. No poner contacto o texto esencial fuera de esa zona.

Carrusel: data.slides con tipo portada/foto/producto/dato/contenido/cierre y los campos directamente en cada slide. Todos con la misma proporción, de 3 a 6 imágenes normalmente. Secuencia usa esas mismas diapositivas en story. PDF: plantilla presentacion y data.slides [{plantilla: "tecnico", data: {...}}], de 1 a 20 páginas; usa los mismos moldes. No crear otro motor.

## Las fotos y sus límites

Hay 17 imágenes originales extraídas del folleto en assets/banco y catalogadas en referencias/fotos.json. Inspeccionadas visualmente. No son fotos de una visita concreta ni certifican que una persona sea cliente de DLA. El encuadre es una propuesta: revisar el PNG y ajustarlo si corta el sujeto. Las piezas ya compuestas del ZIP son referencia, no fondos para poner otro texto encima.

Silotrato, RaniWrap, Ambic y Bekina tienen imágenes de producto reales. Mantener etiqueta, proporciones, color y envase. Usar contain en producto. Una foto de producto no debe pasar por IA para recrear su etiqueta. Si el usuario acordó un recorte, usar exactamente ese archivo; si sólo pidió una placa, no encargar una edición o generación innecesaria.

## Datos y tono

Soluciones integrales para el agro; servicio técnico a campo, conservación de forrajes e higiene y desinfección. Voz profesional, cercana, español uruguayo: "conocé", "consultanos", "te acompañamos". Evitar superlativos, resultados garantizados y beneficios inventados.

El folleto contiene fichas técnicas y algunas afirmaciones comerciales fuertes. No convertirlas automáticamente en recomendaciones de uso, dosificación, seguridad o garantías vigentes. Para una pieza técnica usar información actual confirmada por DLA. No inferir stock, precios, descuentos, certificados o exclusividades actuales.

Mercoláctea de mayo 2025 y la jornada del 13/8/2026 son históricas. No anunciarlas como próximas. Tampoco reutilizar el teléfono de inscripción de una jornada como contacto general. La firma de contacto segura es www.dla.com.uy o @ducartla, confirmados en el perfil actual.

## Entrega

Leer el brief completo y los contratos; escribir spec y renderizar con:
`python3 /app/render.py --marca ducart-disenos SPEC SALIDA`.

Abrir cada PNG y comprobar: logo original legible una vez; texto entero; foto correcta; datos y cifras exactos; producto completo; zona segura; ninguna fecha vieja. Corregir y volver a renderizar si falla. No publicar automáticamente: primero mostrar el resultado y esperar pedido explícito de publicación.
