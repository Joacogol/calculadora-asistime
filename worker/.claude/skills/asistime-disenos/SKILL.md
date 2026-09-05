---
name: asistime-disenos
description: Genera piezas de diseño para las redes de Asistime.ai (@asistime.ai) — la plataforma de agentes de IA de LAiB — con su identidad oficial: azul #4D90FF, violeta #B362FF y el degradado del uno al otro, tinta casi negra, fondo claro, una sola tipografía (Red Hat Display) y el slide oscuro de impacto usado con cuentagotas. Cinco plantillas —titular, dato, testimonio, producto y cierre— que también son las diapositivas de sus carruseles y secuencias. Usar SIEMPRE que se pida una placa, carrusel, story o reel para Asistime.
---

# Asistime

La plataforma de agentes de IA de LAiB. Le habla a dueños de pymes y
emprendedores; lo que cada pieza tiene que dejar es **alivio**: «esto me
devuelve tiempo».

Es el primer cliente que entró **entero como datos** —sin una línea de Python
propia— y a la vez la marca de la casa: lo que salga de acá va al feed de
@asistime.ai. Las reglas están en `marca.json` (`cuidados`) y mandan sobre
este archivo.

## La identidad (kit oficial, 3/9/2026)

- **Dos colores y un degradado.** Azul `#4D90FF`, violeta `#B362FF`, y el
  degradado de uno al otro. El azul es el acento de todos los días. El
  violeta aparece SOLO dentro del degradado: en la palabra destacada de un
  título, en el número del dato, o en el botón. Nunca como color plano suelto,
  y **nunca como fondo entero de una pieza**: a sangre completa el degradé sale
  un azul claro que no es el de Asistime.
- **Una tipografía: Red Hat Display.** ExtraBold en lo que se lee primero,
  Regular y Medium en lo que se lee después. Los seis pesos estáticos están en
  `fonts/` (licencia OFL) y son los mismos que usa el reel para sus rótulos.
- **Clara por defecto, con UN fondo de impacto.** El de todos los días es el
  blanco con un dejo azul-violeta y dos manchas de luz desenfocadas. El de
  impacto es el navy con resplandor que baja a violeta: es el que la marca
  reconoce como propio y va cuando la pieza tiene que frenar el pulgar
  —expectativa, un anuncio, un lanzamiento, el cierre de una serie, el dato que
  duele—. En una misma serie va salteado, nunca dos veces seguidas.

  **Los nombres del `estilo` no describen el fondo, así que no elijas por el
  nombre: elegí por para qué es la pieza.** `oscuro` y `degrade` llevan los dos
  al fondo de impacto, a propósito. `claro` es el de todos los días y `azul` es
  el azul pleno. El catálogo los lista con su para-qué.
- **El logo viene pintado.** Isotipo y lockup son PNG en dos versiones
  (color y blanco); el motor elige la blanca sobre fondo oscuro. El azul del
  logo (`#006AFF`) no se usa para nada más.

## Las cinco plantillas

| | |
|---|---|
| `titular` | un claim grande, con UNA palabra en el degradé; sobre claro, sobre foto o sobre video (el rótulo del reel). La pieza de todos los días. |
| `dato` | el slide oscuro de impacto: un número grande en el degradé y una frase. Salteado: nunca dos veces seguidas. Siempre con fuente. |
| `testimonio` | la cita textual de un cliente, con su nombre, su negocio y —si lo hay— el número que ganó. La prueba social. |
| `producto` | el agente en acción: una conversación de WhatsApp o Instagram dibujada dentro de una tarjeta, con el claim arriba. Mostrar en vez de decir. |
| `cierre` | el CTA: «Hablá con Tony», el lockup y la web. Va al final. |

## Carruseles y secuencias

Se piden como formato (`carrusel`, `secuencia`), no como plantilla. Cada
diapositiva lleva un `tipo` y **los campos de la plantilla que la dibuja**
(`identidad.carrusel.diapos` en `marca.json`):

| tipo | plantilla | para qué |
|---|---|---|
| `portada` | `titular` | la primera: la pregunta que interpela, con una palabra en el degradé |
| `texto` | `titular` | una idea por diapositiva |
| `dato` | `dato` | el número que duele, una vez por serie |
| `testimonio` | `testimonio` | la prueba social, en el lugar de la «solución» |
| `producto` | `producto` | el agente resolviéndolo |
| `cierre` | `cierre` | «Hablá con Tony». En el fondo de impacto si la serie venía clara |
| `cuadro` | `titular` | el defecto de una secuencia de stories |

La estructura que funcionó en el feed real, en seis: gancho (`portada`) →
criterio (`texto`) → dato (`dato`) → solución (`testimonio` o `producto`) →
cierre. El índice y las flechas los pone el motor; sobre el `dato` y sobre
un cierre de impacto salen en blanco solos.

## Lo que no se hace

- No se inventa otro CTA: es «Hablá con Tony».
- No se usa el violeta plano ni un tercer color. No se mezcla otra tipografía.
- No se promete un resultado de negocio; se promete tiempo.
- No se publica un dato sin fuente ni un testimonio sin nombre.
