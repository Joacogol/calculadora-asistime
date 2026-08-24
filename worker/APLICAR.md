# Cómo aplicar esta migración al worker

Los archivos de esta carpeta van en las mismas rutas del repo del worker.
Verificado el 24/8/2026: **las 14 plantillas × 4 formatos = 56 renders salen
byte por byte idénticos** a los de antes.

## Qué cambia

| Archivo | Qué |
|---|---|
| `motor/plantillas.py` | **nuevo** — carga plantillas que son datos y las devuelve como funciones `(data, fmt) -> html`, la misma firma de siempre |
| `.claude/skills/boss-padel-disenos/plantillas/` | **nuevo** — 12 plantillas, cada una con su `plantilla.html` y su `plantilla.json` |
| `templates.py` | 823 → 292 líneas. Quedan `duelo` y `horarios`, que son programas |
| `marca.py` | junta las dos fuentes y expone `CATALOGO()` |
| `marca.json` | agrega `asistime.catalogo` con el id del documento (831) |
| `herramientas/publicar-catalogo.py` | **nuevo** — republica el catálogo como Documento de Asistime |
| `requirements.txt` | agrega `jinja2>=3.1.0` |
| `plantillas.sql` | **nuevo** — la tabla de plantillas versionadas, para la base de cada cliente |
| `app/plantillas.py` | **nuevo** — baja las plantillas publicadas al skill en cada corrida |
| `app/chat.py` | dos líneas: `plantillas.limpiar()` en el ciclo y `plantillas.sincronizar()` antes de diseñar |
| `herramientas/sembrar-plantillas.py` | **nuevo** — sube las plantillas del disco a la base y las publica |
| `estudio/` | **nuevo** — el editor con preview real. Ver [estudio/LEEME.md](estudio/LEEME.md) |
| `plantilla-pedidos.sql` | **nuevo** — la cola de pedidos de plantilla, para la base de cada cliente |
| `funciones/api-plantillas/` | **nuevo** — la Edge Function por donde Asistime pide y consulta |
| `app/plantillero.py` | **nuevo** — atiende un pedido: escribe la plantilla, la dibuja, la mira y la corrige |
| `herramientas/previsualizar-borrador.py` | **nuevo** — dibuja un borrador; es lo que le deja al plantillero **ver** lo que escribió |

Nada de `motor/` se toca fuera de agregar un archivo. El bucle de render, el
video, los efectos, los carruseles y las presentaciones quedan igual.

## Aplicar

```bash
cp -r worker/* /ruta/al/repo/del/worker/
cd /ruta/al/repo/del/worker
pip install jinja2
```

## Verificar antes de desplegar

La regla es una sola: **si el PNG no da el mismo MD5, no está migrada.**

```bash
cd .claude/skills/boss-padel-disenos
git stash                       # el motor de antes
python3 render.py ejemplo-spec.json /tmp/base
git stash pop                   # el motor de ahora
python3 render.py ejemplo-spec.json /tmp/nuevo
for f in /tmp/base/*.png; do
  n=$(basename $f)
  [ "$(md5sum $f|cut -d' ' -f1)" = "$(md5sum /tmp/nuevo/$n|cut -d' ' -f1)" ] \
    && echo "OK $n" || echo "DISTINTO $n"
done
```

## Una vez, para que la base tome el mando

```bash
# 1 · la tabla, en el SQL Editor del Supabase del cliente
#     (pegá plantillas.sql)

# 2 · sembrarla con lo que trae el despliegue
python3 herramientas/sembrar-plantillas.py boss-padel-disenos --probar
python3 herramientas/sembrar-plantillas.py boss-padel-disenos
```

En Boss ya está la tabla creada y `tip` publicada como versión 1 —la prueba de
punta a punta—. Las otras once las sube ese comando: usa las mismas claves que
el worker, así que corre con el mismo entorno.

**El orden importa.** A partir del momento en que una plantilla está publicada
en la base, la base manda: el worker la baja al skill en cada corrida y pisa la
del despliegue. Una plantilla que NO está en la base se queda como vino en el
despliegue — la base pisa lo que trae, lo que no trae no lo toca, y nunca borra.

## Después de desplegar

```bash
ASISTIME_CLAVE=… python3 herramientas/publicar-catalogo.py boss-padel-disenos
```

Es idempotente: si el catálogo no cambió no escribe una versión nueva. Conviene
que quede al final de `desplegar-chat.sh`.

## Qué es cada archivo de una plantilla

```
plantillas/torneo/
├── plantilla.html    el diseño, con {{ campos }}
└── plantilla.json    formatos, medidas por formato, campos y notas
```

Dentro del HTML hay disponible:

| | |
|---|---|
| `d.<campo>` | los datos, con los valores por defecto ya aplicados |
| `m.<medida>` | las medidas del formato que se está dibujando |
| `c.<color>` | los colores de la marca (`c.lima`, `c.negro`…) |
| `ac` | el color de acento ya resuelto |
| `fmt` | `post`, `vert`, `story` o `reel` |
| `t` | el contrato entero, para lo que la plantilla guarde ahí (los íconos de `destacada`, por ejemplo) |
| `logo()` `aros()` `blob()` | los helpers gráficos de la marca |
| `plan_titular()` | mide la foto y dice si el titular necesita bloque sólido |

Una plantilla no puede inventar un color ni una tipografía: compone con el
vocabulario que ya existe. Eso es lo que la mantiene on-brand.

## Lo que quedó afuera a propósito

`duelo` y `horarios` siguen en Python. No es deuda: `horarios` elige el cuerpo
tipográfico y la cantidad de columnas según cuántas horas entran, y `duelo` mide
las fotos y arma su propia estructura. Eso no es un diseño con variables, es un
programa. Lo que tienen de reutilizable —una grilla que se autoajusta— conviene
subirlo a `motor/` como primitiva; recién ahí vuelven a ser datos.

## Un cabo suelto que apareció migrando

`americano` hace desaparecer `precio` si viene vacío, rótulo incluido. La regla
de marca del 12/8/2026 dice que en los anuncios de torneos siempre tiene que
figurar el precio por pareja. Si un americano cuenta como «anuncio de torneo» lo
tiene que decir el club — y si la respuesta es sí, la corrección es una línea:
poner `"requerido": true` en el campo `precio` de `plantillas/americano/
plantilla.json`. Es exactamente la clase de cosa que el contrato resuelve una
vez, en vez de depender de que el agente se acuerde de una regla escrita en otro
documento.


## Verificado de punta a punta

Contra una base de prueba, con el cliente HTTP real y no simulado:

| Prueba | Resultado |
|---|---|
| Borrar `tip` del disco y correr la corrida | vuelve de la base con el mismo MD5 |
| Renderizar las 14 con `tip` viniendo de la base | 56 / 56 idénticos |
| Correr la sincronización dos veces | la segunda no toca el disco |
| Una base sin la tabla (el caso de Clínica) | log informativo, sigue con las del despliegue |
| Una base que no contesta | warning, sigue con las del despliegue |

Un detalle que apareció y no molesta: Postgres guarda `jsonb` sin conservar el
orden de las claves, así que el `plantilla.json` que baja de la base tiene el
mismo contenido con las claves en otro orden. El render es idéntico —está
probado— y `sembrar-plantillas.py` compara los datos, no el texto, así que no
vuelve a subir una plantilla por eso. Lo único que pasa es que el archivo se
reescribe una vez después del primer despliegue y después queda estable.


## El estudio

```bash
python3 -m estudio.servidor boss-padel-disenos     # http://localhost:8080
```

Levanta un Chromium y no vuelve a cerrarlo, así que el primer arranque tarda
unos segundos y después cada preview sale en menos de un segundo. Usa las mismas
claves que el worker para publicar.

Detalle de despliegue: es un servicio, no un job — escucha en `$PORT` y no
termina. Va como un Cloud Run **service** aparte, con la misma imagen del worker.

Lo que hace y lo que todavía no, en `estudio/LEEME.md`.


## El plantillero: pedir una plantilla desde el chat

`app/plantillero.py` corre en la misma corrida que el diseñador, atiende hasta
dos pedidos por vuelta, y deja el resultado **sin publicar**. La cola es
`plantilla_pedidos` y la puerta es la Edge Function `api-plantillas`.

```bash
# 1 · la cola, en el SQL Editor del Supabase del cliente
#     (pegá plantilla-pedidos.sql — trae el `add column if not exists`, así
#      que también sirve para una base que ya tenía la tabla sin `corrige`)

# 2 · la puerta
supabase functions deploy api-plantillas --no-verify-jwt
```

Usa la misma `API_CLAVE` que `api-disenos`, así que no hay secreto nuevo que
configurar. En Boss ya está desplegada (v2, con `corrige`).

### Los dos pedidos que sabe atender

| El chat manda | El plantillero hace |
|---|---|
| sólo `mensaje` | escribe una plantilla nueva de cero |
| `mensaje` + `corrige: "torneo"` | baja la versión publicada de `torneo` y la **edita** |

La diferencia no es cosmética. Rehacer una plantilla para mover un número de
tamaño la reemplaza por otra parecida: se pierden los campos que alguien ya
mandaba y las decisiones que nadie escribió. Corrigiendo, la plantilla que la
gente usa sigue siendo la misma con el cambio pedido.

### Lo que cuesta, y por qué

La primera corrida real —una plantilla nueva, medida— dio **US$3,50 y 486 s**.
Se fue en tres cosas, y las tres están arregladas:

| Se iba en | Ahora |
|---|---|
| el `SKILL.md` entero cargado como skill: 23.324 tokens releídos en los 43 turnos, de los que servían 590 | `_vocabulario()` arma los colores, los formatos y las clases desde el módulo de marca: 523 caracteres, y no puede quedar viejo porque se genera |
| tres plantillas de referencia, cada una releída en todos los turnos siguientes | dos |
| cuatro formatos por ronda × cuatro rondas = 43.184 tokens de imagen | `post` y `story` mientras itera, los cuatro una vez al final; y el `ejemplo.json` de caso límite **antes** de la primera ronda, que es lo que baja las rondas de cuatro a dos |

Corregir arranca además sin nada de eso: no lee referencias, no inventa el
contrato, y dibuja para verificar en vez de para descubrir.

### Un preview demasiado pesado tumbaba la corrida

Apareció corriendo un pedido real y es de las que no se ven venir. El agente
escribe los archivos, corre `previsualizar-borrador.py`, va a abrir el PNG
—que es el único momento que importa de todo esto— y el SDK se cae:

```
Failed to decode JSON: JSON message exceeded maximum buffer size of 1048576 bytes
```

Un `story` de 1080×1920 con un fondo ruidoso pesa ~600 KB; en base64 dentro
del mensaje se pasa del megabyte. Y como se cae **después** de escribir los
archivos, el borrador queda: parece que salió bien y lo que sale es una pieza
que nadie miró.

`previsualizar-borrador.py` ahora achica la copia que se mira —por lado (900 px)
y por peso (350 KB), bajando de a poco hasta que entre—. La pieza se dibuja
siempre a tamaño real: lo que se achica es la copia, después de medir. Los
previews que se suben y ve la persona salen de `_dibujar()` y siguen enteros.

De paso baja el costo donde más pesaba: el preview de `story` pasa de 2.764 a
607 tokens de imagen, y esos se releen en todos los turnos que siguen.

### El modelo

```
MODELO_PLANTILLERO   claude-opus-5      plantilla nueva
MODELO_CORRECTOR     claude-sonnet-5    corrección
```

Se corrió **la misma plantilla con los dos**, cambiando sólo esa variable:

| | Opus 5 | Sonnet 5 |
|---|---|---|
| Costo | US$3,50 | US$1,19 |
| Tiempo | 486 s | 323 s |
| Turnos | 43 | 47 |

Las dos piezas salieron correctas y on-brand. Donde se separaron fue en el
problema difícil —el nombre del día que no entra en una línea—: Sonnet lo
aceptó como límite y lo dejó anotado en el contrato; Opus lo resolvió
calculando el cuerpo tipográfico según el ancho del texto, y además dejó dos
campos opcionales como los deja el resto de la marca.

Por eso el default se parte en dos: una plantilla se escribe una vez y se usa
cien, así que ahí el modelo bueno se paga solo; una corrección es un cambio
acotado sobre algo que ya funciona, y ahí no compra nada. Cualquiera de los dos
se cambia por variable de entorno sin tocar código.

