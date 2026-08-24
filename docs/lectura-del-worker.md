# Lectura del worker

Lo que cambia del plan después de leer el repo real. 24/8/2026.

Hasta acá había trabajado sobre el skill sincronizado —6 plantillas, sin
`motor/`—. Con el repo a la vista hay cuatro correcciones que hacer, dos a favor
y dos en contra.

---

## 1. A favor · la arquitectura ya está bien separada

`motor/` es de verdad agnóstico de marca, y ya tiene un contrato declarado en
`motor/contrato.py`: una marca tiene que exponer `C`, `FORMATOS`, `BASE_CSS`,
`PLANTILLAS` y `logo()`, y `verificar()` falla temprano con un mensaje
entendible si falta algo. `marca.json` ya saca los datos del club a un archivo
de datos, con el motivo escrito adentro.

O sea que el trabajo de separar lo compartido de lo propio de cada marca **ya
está hecho**, y bien. Lo que falta es un nivel más abajo: el contrato es de la
marca, no de la plantilla. El motor sabe que `PLANTILLAS` tiene que existir;
nadie declara qué campos necesita `torneo`.

Esa es exactamente la pieza que falta, y encaja donde ya hay lugar para ella.

## 2. A favor · 12 de las 14 plantillas son datos

Conté la lógica de control de cada una:

| Plantilla | Líneas | Veredicto |
|---|---:|---|
| torneo, agenda, countdown, tip, destacada | 18–51 | datos |
| resultados, titular, tipografica, promo, campeones, americano, socio | 19–88 | datos + una lista |
| **duelo** | 73 | **programa** |
| **horarios** | 139 | **programa** |

`horarios` no es una plantilla con variables: cuenta cuántas horas hay que
meter, elige el cuerpo tipográfico según ese total, y elige la cantidad de
columnas minimizando las huérfanas de la última fila. `duelo` tiene su propia
función interna y cuatro llamadas a `max`/`len`.

**Esas dos no se migran a plantilla-como-datos, y no hay que forzarlas.** Su
lógica de composición es genérica —una grilla que se autoajusta la quiere
cualquier marca con horarios— así que va a `motor/` como primitiva reutilizable,
que es exactamente lo que el propio `motor/__init__.py` dice que hay que hacer
con lo compartido. Después `horarios` vuelve a ser datos, con un
`{{ grilla(horas) }}` adentro.

## 3. En contra · el catálogo no es una lista de campos

Esto es una corrección a lo que dije antes. La sección «Las 14 plantillas» del
`SKILL.md` son **231 líneas** y no son mecánicas: llevan el oficio.

> `fecha_l2` va con tracking más abierto que `fecha_l1` — es la firma
> tipográfica del club.

> **No es `torneo` con otra fecha.** Un torneo es un evento de tres días y su
> placa es solemne; esto es un jueves a las 20 y tiene que sonar a plan, no a
> competencia.

> Es la plantilla que más plata deja: los formatos estructurados se venden entre
> 40 y 50% por encima de la reserva de cancha suelta.

Nada de eso sale de un `plantilla.json` con campos y tipos. Si la migración
genera el catálogo sólo desde los campos, **se pierde la mejor parte del skill**.

La salida es que el contrato lleve un campo `notas` en markdown, que se copia
tal cual del `SKILL.md` y se sigue editando ahí. El catálogo generado queda:
campos declarados —que es lo que hoy se desincroniza— más notas escritas por una
persona —que es lo que hoy vale—.

## 4. En contra · generar una plantilla da un esqueleto, no una plantilla buena

La `americano` que generé de un pedido ya existía en producción, hecha a mano.
No lo sabía cuando la hice, así que salió una comparación honesta.

**El contrato coincidió casi entero:** día, hora, sede, precio, cupos, cta,
acento, foto. La estructura del problema la agarró sola.

**El oficio no.** La de producción va sobre el azul de marca en vez de una foto
oscura, pone los cupos en un recuadro, el llamado a la acción en un bloque lima
sólido, los aros gigantes como marca de agua, y suma lo que incluye. La mía es
correcta y sosa.

Está en `prototipo/CMP-generada-vs-real.png`.

La conclusión no debilita la propuesta, la ordena: **el generador da un punto de
partida estructuralmente correcto, no una plantilla terminada.** Por eso el
bucle importa más que el generador, y por eso publicar tiene que ser una
decisión de una persona. Un diseñador que corrige tres veces un esqueleto
correcto llega antes que uno que arranca de un archivo vacío — pero llega él, no
el generador.

---

## Un cabo suelto que encontré

La plantilla `americano` de producción hace desaparecer `precio` si viene vacío,
rótulo incluido. La regla de marca del 12/8/2026 dice que en los anuncios de
torneos siempre tiene que figurar el precio por pareja.

Si un americano cuenta como «anuncio de torneo» es discutible y lo tiene que
decir el club. Pero es exactamente la clase de cosa que hoy depende de que el
agente se acuerde de una regla escrita en otro documento, y que con un campo
requerido en el contrato se resuelve una vez. Vale preguntarlo.

---

## El plan corregido

**Etapa 1 · Migrar las plantillas.** De 2–3 días a **1 semana**. Tres razones:
son 12 y no 14; hay que llevar las notas del `SKILL.md` a cada contrato, que es
trabajo de leer y decidir, no de copiar; y `duelo` y `horarios` necesitan la
primitiva de grilla en `motor/` antes de poder volver a ser datos.

La regla del prototipo se mantiene y es lo que hace que esto sea seguro: si el
PNG no da el mismo MD5, no está migrada.

El resto del plan no cambia.
