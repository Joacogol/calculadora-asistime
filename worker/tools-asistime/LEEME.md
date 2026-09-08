# El código de las tools de Asistime

Cada tool de un agente de Asistime es un pedazo de JavaScript que vive **en la
base de Asistime**, no acá. Se edita desde su panel y no tiene historial que se
pueda leer con `git log`.

Esta carpeta existe por eso: para que ese código **también** esté versionado.
No se despliega desde acá —Asistime no lee este repo— pero acá se ve qué
cambió, cuándo y por qué, que es justamente lo que no se ve del otro lado.

**Si tocás una tool en el panel de Asistime, copiá el código acá y commiteá.**
Si las dos copias se separan, la que manda es la de Asistime (es la que corre) y
ésta pasa a ser una mentira prolija, que es peor que no tener nada.

## Dos reglas del sandbox, que costaron caro

El sandbox de Asistime **no es Node ni el navegador**, y se parece lo suficiente
como para engañar. El 1/9/2026 `ver_reel` devolvió «Error» en el simulador, sin
una línea más, mientras los registros del otro lado mostraban que la API había
contestado 200: la respuesta llegaba bien y algo se rompía después. El mismo
código corre sin una queja fuera de ahí, así que no había forma de reproducirlo.

1. **Leer el cuerpo con `try { d = await r.json() } catch`,** nunca con
   `await r.json().catch(...)`. Es el único idioma que usan las herramientas
   que funcionan hace semanas, y era lo único que estas dos hacían distinto.
2. **Nunca devolver `null`.** Un reel sin placa de cierre devolvía
   `cierre: null`; mandar `""` cuesta nada.

Y la que vale para todas: **envolver la herramienta entera en un `try`** que
devuelva el error en castellano. Una tool que muere diciendo «Error» y nada más
no se puede arreglar desde afuera — ni por quien la usa, ni por quien la
escribió. Si se rompe, que diga por qué.

En general: **no estrenar construcciones de JavaScript acá.** Copiá el idioma de
una tool que ya esté corriendo en producción.

| Archivo | Tool | Tenant | Id |
|---|---|---|---|
| `ver_reel.js` | `ver_reel` | 119 (Boss Padel) | 2143 |
| `retocar_reel.js` | `retocar_reel` | 119 (Boss Padel) | 2144 |
| `estado_reel-stadium.js` | `estado_reel` | 176 (Stadium) | 2076 |
| `crear_diseno-asistime.js` | `crear_diseno` | 1 (Asistime) | 2166 |
| `montar_reel-asistime.js` | `montar_reel` | 1 (Asistime) | 2189 |
| `publicar_diseno-asistime.js` | `publicar_diseno` | 1 (Asistime) | 2205 |
| `publicar_reel-asistime.js` | `publicar_reel` | 1 (Asistime) | 2206 |
| `publicar_archivo-asistime.js` | `publicar_archivo` | 1 (Asistime) | 2207 |
| `estado_publicacion-asistime.js` | `estado_publicacion` | 1 (Asistime) | 2208 |
| `montar_reel-larrique.js` | `montar_reel` | 80 (Larrique) | 2258 |

Todas hablan con `funciones/api-reels`, con la clave `API_CLAVE` del proyecto
de Supabase del cliente escrita en el código. Eso es a propósito y está
explicado en `DESPLEGAR.md`: el sandbox de Asistime no tiene secretos, así que
la clave está en claro y lo que la protege es que la función del otro lado sea
angosta — no puede borrar nada ni leer nada que no sea de reels.

## Lo que hay en los otros dos clientes

El 1/9/2026 se emparejaron Stadium y Clínica con Boss. Sus `montar_reel`,
`ver_reel` y `retocar_reel` son **el mismo código de acá con la URL y la clave
del proyecto cambiadas**, así que no se copian: duplicar tres archivos por
cliente convierte esta carpeta en cinco versiones de lo mismo, y a la primera
corrección quedan cuatro desactualizadas. Lo que sí queda anotado es dónde
están:

| Tool | Boss (119) | Stadium (176) | Clínica (73) |
|---|---|---|---|
| `montar_reel` | ya existía | 2149 | 2153 |
| `ver_reel` | 2143 | 2150 | 2154 |
| `retocar_reel` | 2144 | 2151 | 2155 |
| `estado_reel` | ya existía | 2076 | 2152 |

## `corregir_diseno` (7/9/2026)

Cambiar UNA cosa de una pieza que ya salió, sin rehacerla. Es a `crear_diseno`
lo que `retocar_reel` es a `montar_reel`.

**Por qué es una tool y no un campo.** `crear_diseno` de Asistime acepta
`corrige` desde el 5/9/2026, pero las de Boss, Stadium y Clínica nunca lo
mandaban: en tres de los cuatro clientes un pedido de cambio entraba como
pedido nuevo y volvía otra pieza. Un campo opcional se saltea; un verbo con
nombre propio se elige. Agregarle el campo a las tres tools habría significado
reescribir a mano tres archivos de producción de 5 KB cada uno — la clase de
transcripción que ya salió mal antes.

| Tenant | Tool | Estado |
|---|---|---|
| Boss 119 | `corregir_diseno` **2234** | falta tildarla en el agente |
| Stadium 176 | `corregir_diseno` **2235** | falta tildarla en el agente |
| Clínica 73 | `corregir_diseno` **2236** | falta tildarla en el agente |
| Asistime 1 | — | lo hace `crear_diseno` (2166) con su campo `corrige` |

El código es `corregir_diseno.js`, con la URL y la clave como marcadores: cada
cliente tiene la suya, y son las mismas que ya usa su `crear_diseno`.

Se probó contra las tres APIs con un id inválido —que no crea ninguna fila—: las
tres contestan 400 diciendo que `corrige` tiene que ser el id de un diseño que
ya se hizo.

Asistime (tenant 1, agente 594) las tiene desde el 2/9/2026: `montar_reel`
**2189** (la versión nueva, con `instruccion` y `duracion`: ver
`montar_reel-asistime.js`), `ver_reel` 2187, `retocar_reel` 2188 y
`estado_reel` 2177. Es el primer cliente con Gemini eligiendo los tramos y
con el encuadre por caras; los demás se emparejan copiando la tool nueva con
su URL y su clave.

`estado_reel-stadium.js` sí está copiado porque **no es el mismo código**.
Stadium es el único cliente con las dos formas de hacer un reel: `crear_reel`,
que lo genera una IA a partir de una foto —cinco minutos, gasta créditos, puede
deformar el producto—, y `montar_reel`, que edita lo que filmaron —dos minutos,
no gasta nada, no hay nada inventado—. La misma tool contesta por los dos, así
que se ramifica con el `montado` que devuelve la API.

Sin esa rama, a quien montó un video propio se le decía «miralo entero, la IA a
veces deforma el producto»: lo mandaba a buscar un problema que no puede
existir, sobre material que filmó él mismo.


## Life Montevideo (8/9/2026)

El tenant 48 ya existía con dos agentes de atención en WhatsApp —Nico [Socios]
66 y Mara [No socios] 67— y siguen intactos. El diseñador entró como un agente
APARTE: **604, «Diseñador Life Montevideo»**, con doce herramientas propias.

| Tool | Id | Qué hace |
|---|---|---|
| `crear_diseno` | 2237 | encarga una pieza |
| `estado_diseno` | 2238 | cómo va |
| `corregir_diseno` | 2239 | cambia una cosa sin rehacerla |
| `montar_reel` | 2240 | edita lo que filma el club |
| `estado_reel` | 2241 | cómo va el montaje |
| `ver_reel` | 2242 | qué dice cada subtítulo |
| `retocar_reel` | 2243 | corrige sin volver a transcribir |
| `editar_foto` | 2244 | los cinco verbos sobre una foto |
| `estado_foto` | 2245 | cómo va la edición |
| `crear_plantilla` | 2246 | un molde nuevo o un cambio |
| `estado_plantilla` | 2247 | cómo va el molde |
| `avisar_cambio_motor` | 2248 | lo que necesita código |

**No se copiaron de Stadium, se escribieron de nuevo**, y es lo que recomienda
el propio `herramientas/alta.py` cuando las marcas son distintas: las de
Stadium hablan de championes, de precios en el epígrafe y de 34 tiendas.
Copiadas con un buscar-y-reemplazar, un club de gimnasia habría quedado con un
agente que razona sobre retail.

Tres cosas quedaron fuera, y cada una por una razón escrita en el código:

- **`crear_reel` y `crear_video`** — generar video con IA. Este club filma; un
  reel de gente entrenando inventado por un modelo no es este club.
- **`crear_foto`** — inventar una foto de cero. Por lo mismo: una cara generada
  publicada como si fuera un socio es un problema distinto al de una pieza fea.
- **`publicar_*`** — Instagram todavía no está conectado para esta cuenta. El
  prompt del agente lo dice con todas las letras en vez de dejarlo fallar.

Las doce apuntan al Supabase de la casa (`qxjvtxumkljsroukpkny`) con la clave de
Life, que vive hasheada en `public.claves_api`. Es el primer cliente que no
tiene proyecto propio: ver `alta/ESQUEMA-COMPARTIDO.md`.

El prompt del 604 está escrito a mano y por eso `marca.json` NO declara
`asistime.agente` — así `publicar-prompt.py` no lo pisa con el genérico, que
prometería las herramientas que este agente no tiene. El catálogo sí se
republica solo en cada despliegue.


## Larrique (tenant 80), 8/9/2026

El agente **605** tiene cinco herramientas y ninguna se copió tal cual:

| Tool | Id | De dónde salió |
|---|---|---|
| `crear_diseno` | 2250 | la de Life, con el formato por defecto en `vertical` (1080×1350, el del feed de Larrique) en vez de `story` |
| `estado_diseno` | 2251 | la de Life, sin cambios más que la clave |
| `corregir_diseno` | 2252 | la de Life, sin cambios más que la clave |
| `montar_reel` | 2258 | **escrita para este cliente** — ver `montar_reel-larrique.js` |
| `estado_reel` | 2259 | la de Boss, sin la rama de `crear_reel`: acá no se genera video con IA, así que no hay nada que advertir sobre caras deformadas ni créditos gastados |

`montar_reel` es el único archivo que se guarda, y va contra la regla de arriba
de no duplicar a propósito: **no es la misma tool con otra URL**. Acá el
material normal son FOTOS de producto, no clips filmados, y eso cambia lo que
manda: un reel de fotos no tiene audio, así que pide `subtitulos: []` y
`cortar_silencios: false`. Sin eso el worker se pone a escuchar tres imágenes.

Faltan `ver_reel` y `retocar_reel`, y no por olvido: las dos existen para
corregir SUBTÍTULOS, y un reel armado con fotos no tiene ninguno. Cuando
Larrique empiece a mandar video filmado, se copian de Boss.

**El primer campo se llama `material` y no `clips`.** El agente lee el nombre
del parámetro antes que su descripción, y con «clips» mandaba a preguntar por
videos a un cliente que sólo tiene fotos.
