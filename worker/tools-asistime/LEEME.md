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

| Archivo | Tool | Tenant | Id |
|---|---|---|---|
| `ver_reel.js` | `ver_reel` | 119 (Boss Padel) | 2143 |
| `retocar_reel.js` | `retocar_reel` | 119 (Boss Padel) | 2144 |
| `estado_reel-stadium.js` | `estado_reel` | 176 (Stadium) | 2076 |

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

`estado_reel-stadium.js` sí está copiado porque **no es el mismo código**.
Stadium es el único cliente con las dos formas de hacer un reel: `crear_reel`,
que lo genera una IA a partir de una foto —cinco minutos, gasta créditos, puede
deformar el producto—, y `montar_reel`, que edita lo que filmaron —dos minutos,
no gasta nada, no hay nada inventado—. La misma tool contesta por los dos, así
que se ramifica con el `montado` que devuelve la API.

Sin esa rama, a quien montó un video propio se le decía «miralo entero, la IA a
veces deforma el producto»: lo mandaba a buscar un problema que no puede
existir, sobre material que filmó él mismo.
