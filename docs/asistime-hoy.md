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

## Lo único que falta

**El que escribe la plantilla.** `app/plantillero.py` en el worker: toma el
pedido, arma la plantilla con el vocabulario de la marca y el catálogo
delante, **la renderiza con el motor de producción, la mira y la corrige**, y
guarda el borrador con su preview.

Hoy un pedido entra y queda en `pendiente` para siempre, porque no hay quien lo
atienda. Todo lo que está antes y después de ese paso ya funciona.

Es un llamado al Agent SDK, igual que `disenador.py`. No lo escribí porque no
lo puedo correr sin la clave de Anthropic, y este proyecto ya aprendió lo que
cuesta dar por hecho código que nunca se ejecutó.
