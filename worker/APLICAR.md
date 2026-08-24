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
