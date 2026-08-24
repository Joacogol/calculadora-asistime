# `clase` — la primera plantilla que se armó sola

Salió de este pedido, escrito en castellano:

> «Necesito una plantilla para anunciar las clases: el nombre del profe, el
> día y la hora, la sede, el nivel y cuánto sale. Con foto del profe si hay.»

Corrida real el 24/8/2026 con `claude-opus-5`.

| | |
|---|---|
| Tiempo | 486 s |
| Turnos | 43 |
| Costo | US$ 3,50 |
| Rondas de dibujo | 4 |

![Con foto](preview-post.png)
![En story](preview-story.png)
![Sin foto del profe](sin-foto.png)

## Lo que decidió, contado por él

> Tomé `socio` para la estructura y `campeones` para las filas rotuladas con
> hilo. El héroe es **el profe**, no la fecha: a una clase uno se anota con
> alguien, y así queda claramente distinta de `americano` —donde el día es el
> titular— y de `titular`, que es la idea de las clases sin datos duros.

Requeridos: `profe`, `dia`, `hora`, `sede`. Opcionales: `nivel` (sale entre
corchetes, a lo `torneo`), `precio` con su unidad, `foto`, `foco`, `kicker`,
`cta`, `contacto` —el teléfono no va por defecto— y `fondo`.

## Las tres cosas que arregló después de mirarla

Esto es lo que justifica todo el diseño del sistema. Ninguna de las tres se ve
leyendo el código:

1. **El día largo se partía en tres líneas en `story`.** «LUNES, MIÉRCOLES Y
   VIERNES» no entra a ningún tamaño de tabla, así que el cuerpo de día+hora
   ahora **se calcula del texto** contra el ancho útil de 928 px. Es la misma
   clase de solución que usa `horarios`, y la encontró solo.
2. **Sin foto quedaba medio metro de azul vacío arriba.** Ahora el bloque se
   centra cuando no hay foto y se apoya abajo cuando la hay.
3. **El nombre de 14 caracteres rozaba el margen.** Baja un escalón antes.

Se armó un `ejemplo.json` de caso límite —nombre largo, tres días, sede de tres
palabras— para forzar esos bordes. Está acá al lado.

## Por qué esta carpeta no está en `plantillas/`

Porque el motor cargaría la plantilla y empezaría a usarla sin que nadie la
haya aprobado, que es exactamente lo que el sistema evita. El camino correcto
es que el pedido lo atienda el worker: deja la versión **sin publicar** en la
base, con su preview, y una persona decide.

El pedido `cf49f0af` sigue **pendiente** en la base de Boss a propósito: cuando
despliegues, el worker lo va a atender de verdad —con la subida del preview
incluida, que es lo único de la cadena que no pude hacer desde acá por no tener
la `service_role`.
