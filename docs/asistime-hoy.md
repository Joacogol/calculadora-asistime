# Cómo está armado Asistime hoy, y qué hay que cambiar

Leído de la API el 24/8/2026, tenant 119. Nada de esto es de memoria.

---

## Lo que hay

**Tres agentes.**

| id | Nombre | Qué es | Prompt |
|---|---|---|---|
| 363 | BOSS Padel | el que atiende de verdad | v7, publicada el 13/8 |
| 364 | Diseñador Boss Padel | el diseñador | v6, publicada ayer |
| 366 | Planeador de redes | analiza Instagram de la competencia | v… (aparte) |

**Tres documentos.** 739 Sedes y Contactos · 779 Reglas de marca · 831 Catálogo
de plantillas.

**Ocho herramientas**, repartidas así:

| Herramienta | 363 | 364 |
|---|:--:|:--:|
| `crear_diseno` · `estado_diseno` · `publicar_diseno` · `estado_publicacion` | ✔ | ✔ |
| `avisar_cambio_motor` | ✔ | ✔ |
| `anotar_regla` | — | ✔ |
| `disponibilidad_canchas` · `solicitar_evento` | ✔ | — |

Y desde ayer, el 363 delega en el 364 con la herramienta `disenador`.

---

## Cinco cosas viejas, de la más grave a la menos

### 1 · El 363 tiene instrucciones para una herramienta que no tiene

Su prompt dedica una sección entera a `anotar_regla`:

> «El manual de marca del club lo podés escribir vos, con anotar_regla. […]
> Después de anotarla, confirmale a la persona qué quedó escrito.»

**`anotar_regla` no está entre sus siete herramientas.** Lo verifiqué leyendo.

Un agente al que se le dice que use una herramienta que no tiene hace
exactamente lo que documenta el traspaso: improvisa con la más parecida y
después cuenta que lo hizo. Es la trampa que ya costó dos tardes, sólo que esta
vez está escrita en el prompt.

### 2 · Dos diseñadores compitiendo — y esto lo introduje yo ayer

El 363 tiene las cuatro herramientas de diseño en su propio cinturón **y**,
desde ayer, un sub-agente `disenador` que tiene las mismas. Con las dos vías
disponibles va a hacer una cosa u otra según el día, y ninguna de las dos va a
estar mal desde su punto de vista.

Hay que elegir una. Es la única decisión de este documento que no puedo tomar yo.

### 3 · El catálogo y el Diseñador dicen que una plantilla que falta «se pide y avisan»

El documento 831 termina así:

> «No improvises con la más parecida […]. Registrá el pedido con
> `avisar_cambio_motor`, contá qué haría falta, y seguí con lo que sí se puede.»

Era cierto anteayer. Hoy el sistema puede armar la plantilla. Es la más cara de
las cinco porque le enseña al cliente que no se puede hacer algo que sí se puede.

### 4 · Datos del club escritos en el prompt en vez de en un documento

En el prompt del 363, a mano:

- los tres planes de socio con sus precios ($2.900 / $6.800 / $5.200)
- el alquiler de paletas a $100
- las categorías del torneo de Hípico del **14, 15 y 16 de agosto** — que ya pasó

Eso es criterio y datos: va al manual, donde el club lo edita solo y entra en la
pieza y en la respuesta siguientes. Mientras viva en el prompt, cambiar un
precio nos necesita a nosotros — que es exactamente lo que este proyecto vino a
sacar del medio.

### 5 · `avisar_cambio_motor` quedó demasiado ancha

Su descripción dispara para «una plantilla que no existe», que ya no necesita
código. Tiene que achicarse a lo que de verdad lo necesita: el video, los
efectos, un formato nuevo, la estructura del carrusel.

---

## Lo que falta para pedir una plantilla y que te la entregue

El camino ya existe para las piezas y funciona. Esto es el mismo camino, con
otro objeto: **encargar → esperar → mirar → confirmar.**

```
  «necesito una placa para las clases, con el profe y el horario»
                          │
                  crear_plantilla ──→ fila en `plantilla_pedidos`, pendiente
                          │
                          │   el worker, en la misma corrida que ya hace
                          ▼
        ┌───────────────────────────────────────────┐
        │  escribe la plantilla con el vocabulario  │
        │  de la marca y el catálogo delante        │
        │  ↓                                        │
        │  LA RENDERIZA con el motor de producción  │
        │  ↓                                        │
        │  la mira, la corrige, vuelve a renderizar │
        └───────────────────┬───────────────────────┘
                            ▼
          versión NO publicada en `plantillas` + preview PNG
                            │
                  estado_plantilla ──→ el preview y los campos
                            │
                    «me gusta, publicala»
                            ▼
                  publicar_plantilla(confirmado: true)
```

### Por qué el que la escribe tiene que estar en el worker

Un agente de Asistime podría escribir el HTML y guardarlo con una herramienta.
Sería más lindo —el cerebro en Asistime, versionado— y lo pensé en serio.

No sirve, por una razón: **el que escribe una plantilla tiene que poder mirar lo
que dibujó.** Un agente de Asistime recibe una URL y no puede abrirla; no se
entera de que el titular desbordó ni de que el acento no contrasta con la foto.
El agente del worker sí: renderiza, abre el PNG y corrige. Es el mismo bucle que
hace bueno al diseñador de piezas, y por el mismo motivo.

Lo que queda en Asistime es lo que corresponde: **el pedido, la conversación y
la decisión de publicar.**

### Las tres piezas nuevas

1. **Tabla `plantilla_pedidos`** en la base del cliente. Igual que `disenos`:
   mensaje, estado, resultado, métricas.
2. **`app/plantillero.py`** en el worker, atendido en la misma corrida.
   El borrador queda como versión **no publicada** en `plantillas`, así que se
   puede abrir en el estudio y afinar a mano antes de publicarlo.
3. **Tres herramientas** en Asistime, calcadas de las de diseño:
   `crear_plantilla` · `estado_plantilla` · `publicar_plantilla`.

`publicar_plantilla` lleva `confirmado: true` por la misma razón que
`publicar_diseno`: cambia todas las piezas que se hagan de ahí en adelante. La
diferencia es que esta sí se puede deshacer —las versiones quedan— y conviene
decirlo en el mensaje, porque una vuelta atrás que existe y nadie conoce es lo
mismo que no tenerla.

---

## Lo que no puedo hacer yo

**Probar una conversación.** La API contesta *«Only user actors can create
simulator contacts»*: mi clave es de aplicación, no de usuario. Puedo leer y
escribir la configuración de los agentes; correr el simulador lo tenés que hacer
vos. No cuentes con que lo verifiqué.


---

# Lo que ya quedó hecho

Todo verificado leyendo después de escribir.

## Los dos bugs vivos, cerrados

**El 363 dejó de tener instrucciones para herramientas que no maneja.** Se le
sacaron las cinco de diseño —quedó con `disponibilidad_canchas` y
`solicitar_evento`— y su prompt (v8, publicada) perdió las dos secciones de
diseño. En su lugar tiene una que dice a qué derivar y, sobre todo, **a qué
no**: reservas, disponibilidad, precios de alquiler, clases, membresías,
torneos y eventos los contesta él.

De paso salió del prompt el torneo de Hípico del 14-15-16 de agosto, que ya
pasó, con una línea que explica por qué el calendario se lee del documento:
*«un torneo que ya pasó es peor que no contestar»*.

## El camino para pedir una plantilla, andando

| Pieza | Estado |
|---|---|
| Tabla `plantilla_pedidos` | creada en la base de Boss |
| Edge Function `api-plantillas` | desplegada, misma `API_CLAVE` que las otras |
| `crear_plantilla` (2055) · `estado_plantilla` (2056) · `publicar_plantilla` (2057) | creadas y asignadas al Diseñador |
| Prompt del Diseñador v7 | publicado: ahora arma plantillas en vez de pedirlas |
| Cierre del catálogo | corregido **en el generador**, no a mano |

La función se probó de punta a punta contra la base real:

```
sin clave                  → 401
clave de largo distinto    → 401
pedido demasiado corto     → 400 pedido_incompleto
pedido de verdad           → 201 con id
consultar cómo va          → estado pendiente
publicar sin confirmar     → 428 falta_confirmar
```

El cierre del catálogo se arregló en `motor.plantillas.catalogo()` y no
editando el documento, porque el documento se regenera entero en cada
despliegue: lo que se escriba a mano allá se pierde en el siguiente. Entra
cuando corras `publicar-catalogo.py`.

## El que escribe la plantilla — corrido y verificado

`app/plantillero.py`. Se probó con el pedido real: **486 s, 43 turnos, cuatro
rondas de dibujo, US$ 3,50.** La plantilla que salió está en
[`worker/plantilla-generada/`](../worker/plantilla-generada/) con sus previews.

Lo que importa no es que escribiera HTML: es lo que arregló **después de
mirarlo**. Tres cosas, ninguna visible leyendo el código —el día largo que se
partía en tres líneas en `story`, la mitad de arriba vacía cuando no hay foto,
y el nombre de 14 caracteres pegado al margen—. Para la primera se armó una
solución del mismo tipo que usa `horarios`: calcular el cuerpo tipográfico del
texto en vez de sacarlo de una tabla de formatos.

Eso es exactamente lo que un agente de Asistime no puede hacer, y por lo que
este paso vive en el worker.

### Las defensas, probadas una por una

El worker **no confía** en que el agente haya verificado: renderiza todos los
formatos del contrato antes de guardar nada.

| Si el contrato… | Qué pasa |
|---|---|
| declara un formato que la marca no tiene | rechazado, con la lista de los que sí |
| trae un `id` que no es un slug | rechazado |
| no declara ningún campo | rechazado |
| no dibuja | rechazado — y el motivo va en castellano al chat |

Y una regla de una línea que hace imposible un error entero: **una carpeta que
empieza con guión bajo no la carga el motor.** El borrador vive en
`plantillas/_borrador/` mientras se escribe, así que no puede salir en una
pieza a medio hacer. Se borra al terminar: lo que vale queda en la base.

## Lo que falta

**Desplegar.** El pedido `cf49f0af` sigue pendiente en la base de Boss a
propósito: cuando el worker corra con el código nuevo, lo atiende de verdad —
incluida la subida del preview, que es lo único de la cadena que no pude hacer
desde acá por no tener la `service_role`.

**Y dos cosas para decidir vos:**

- Los **modelos del worker** están dos generaciones atrás: `config.py` tiene
  `claude-sonnet-4-5` y `claude-opus-4-5`. No los toqué. Al plantillero le puse
  `claude-opus-5` en su propia variable, porque una plantilla se escribe una
  vez y se usa cien.
- **El modelo del plantillero.** Está medido, abajo — con los dos, con la misma
  plantilla. El default quedó partido: Opus para escribir una nueva, Sonnet
  para corregir una que ya existe.

## Los US$ 3,50, medidos y bajados

La primera corrida costó eso y no estaba claro en qué. Se midió antes de tocar
nada, y las tres cosas que lo explicaban se arreglaron:

| Se iba en | Cuánto | Qué se hizo |
|---|---|---|
| el `SKILL.md` de Boss cargado entero como skill | 23.324 tokens releídos en los 43 turnos, de los que servían **590** | se sacó. `_vocabulario()` arma colores, formatos y clases desde el módulo de marca: 523 caracteres, y no puede quedar viejo porque se genera |
| las plantillas de referencia | tres, cada una releída en todos los turnos siguientes | dos |
| los previews | cuatro formatos × cuatro rondas = 43.184 tokens de imagen | `post` y `story` mientras itera; y el `ejemplo.json` de caso límite **antes** de la primera ronda, que es lo que baja las rondas de cuatro a dos |

La lectura de caché era el 53% de la factura, y era eso: el skill entero y las
tres referencias, releídos cuarenta y tres veces.

### El modelo, con la pieza delante

Se corrió **la misma plantilla con los dos**, cambiando sólo esa variable:

| | Opus 5 | Sonnet 5 |
|---|---|---|
| Costo | US$ 3,50 | US$ 1,19 |
| Tiempo | 486 s | 323 s |
| Turnos | 43 | 47 |

Las dos piezas salieron correctas y on-brand. Se separaron en el problema
difícil —el nombre del día que no entra en una línea—: Sonnet lo aceptó como
límite y lo anotó en el contrato («si el día es una lista larga, la hora puede
pasar a una línea propia debajo… es intencional»); Opus lo resolvió calculando
el cuerpo tipográfico según el ancho del texto, y además dejó `nivel` y
`precio` opcionales, como los deja `americano`.

Por eso el default quedó así, y cada uno se cambia por variable de entorno:

```
MODELO_PLANTILLERO   claude-opus-5      plantilla nueva
MODELO_CORRECTOR     claude-sonnet-5    corrección
```

Una plantilla se escribe una vez y se usa cien: ahí el modelo bueno se paga
solo. Una corrección es un cambio acotado sobre algo que ya funciona: ahí no
compra nada.

## Corregir, que era lo que faltaba

Hasta acá el sistema sabía hacer plantillas nuevas y nada más. Pero la mitad de
lo que le van a pedir es «a la de torneos hacele el título más grande», y
rehacerla para eso la **reemplaza** por otra parecida: se pierden los campos que
alguien ya mandaba y las decisiones que nadie escribió.

Ahora `crear_plantilla` acepta `corrige` con el id de una plantilla del
catálogo. El worker baja la versión publicada, la deja en el borrador y le pide
que la **edite**: no lee referencias, no inventa el contrato, y dibuja para
verificar en vez de para descubrir.

| El chat manda | Qué pasa |
|---|---|
| sólo `mensaje` | plantilla nueva, de cero, con Opus |
| `mensaje` + `corrige: "torneo"` | se edita la publicada, con Sonnet |
| `corrige` con un id que no está publicado | se arma de cero y queda en el log — el pedido es válido igual |

Está de punta a punta: columna en la base, campo en la Edge Function (v2,
desplegada), parámetro en la tool 2055, y la rama en `plantillero.atender()`.
Probado con un POST real contra la función: el pedido entra con su `corrige` y
vuelve con él al consultar.

