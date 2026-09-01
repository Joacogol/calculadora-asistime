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

Las dos hablan con `funciones/api-reels`, con la clave `API_CLAVE` del proyecto
de Supabase del cliente escrita en el código. Eso es a propósito y está
explicado en `DESPLEGAR.md`: el sandbox de Asistime no tiene secretos, así que
la clave está en claro y lo que la protege es que la función del otro lado sea
angosta — no puede borrar nada ni leer nada que no sea de reels.
