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
