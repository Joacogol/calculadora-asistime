# Lo que quedó armado

24/8/2026. El estado real, no el plan.

---

## 1. El motor · las plantillas salieron del código

**12 de las 14 plantillas de Boss Padel ya no son código.** Cada una es una
carpeta con dos archivos:

```
plantillas/torneo/
├── plantilla.html    el diseño, con {{ campos }}
└── plantilla.json    formatos, medidas, campos y notas
```

`motor/plantillas.py` los interpreta y los devuelve como funciones con la misma
firma de siempre, así que **el resto del motor no se enteró**: el bucle de
render, el video, los efectos, los carruseles y las presentaciones quedaron
intactos. `templates.py` pasó de 823 a 292 líneas.

### Verificado

Las 14 plantillas × 4 formatos, renderizadas con el motor de antes y con el de
ahora, comparadas por MD5:

```
IDÉNTICOS: 56 / 56
```

Y después de borrar el código viejo de `templates.py`, otra vez: 56/56. La regla
es esa y no se negocia: si el PNG no da el mismo MD5, no está migrada.

### Las dos que no migraron, a propósito

`duelo` y `horarios` siguen en Python. `horarios` elige el cuerpo tipográfico y
la cantidad de columnas según cuántas horas entran, minimizando huérfanas en la
última fila; `duelo` mide las fotos y arma su propia estructura. Eso no es un
diseño con variables, es un programa — forzarlo sería inventar un lenguaje de
programación adentro del HTML.

Lo que tienen de reutilizable —una grilla que se autoajusta— va a `motor/` como
primitiva, y recién ahí vuelven a ser datos. Es el siguiente paso, no una deuda.

---

## 2. Asistime · el catálogo es un documento

El catálogo de plantillas se genera de los contratos y vive como **Documento
831** del tenant 119, publicado.

Va como documento y no como herramienta por una razón: una herramienta
necesitaría un endpoint nuevo con su clave escrita en el código de la tool, a la
vista de cualquiera que abra esa pantalla. Un documento ya está versionado, ya
tiene vuelta atrás, ya lo lee el agente y el club lo ve. **La regla del proyecto
sigue en pie: cuando un secreto tendría que vivir en un lugar que no controlás,
mejor no tener el secreto.**

`herramientas/publicar-catalogo.py` lo republica después de cada despliegue, y
es idempotente: si el catálogo no cambió, no escribe una versión nueva. Sin eso
cada despliegue dejaría una versión idéntica y el historial se volvería ilegible
justo cuando hace falta leerlo.

---

## 3. Asistime · el agente Diseñador

El agente **364** dejó de ser el que quedó colgado con la delegación muerta y
pasó a ser el diseñador de verdad.

| | |
|---|---|
| Prompt | versión 6, publicada |
| Documentos | Catálogo de plantillas (831) · Reglas de marca (779) |
| Herramientas | `crear_diseno` · `estado_diseno` · `publicar_diseno` · `estado_publicacion` · `avisar_cambio_motor` · **`anotar_regla`** |

Verificado releyendo, no por lo que devolvió la escritura.

`anotar_regla` entra en servicio por primera vez: estaba creada desde el 12 de
agosto y nunca había quedado asignada a ningún agente.

### Las dos puertas

El prompt separa las dos cosas que la gente pide con las mismas palabras, con la
pregunta del traspaso:

> ¿Es **qué decir o qué elegir**, o es **cómo se ve**?

- **Qué decir o qué elegir** → `anotar_regla`. Entra al manual de marca y la
  pieza siguiente ya sale con el cambio. No espera a nadie.
- **Cómo se ve** → `avisar_cambio_motor`. Queda registrado con qué pieza lo
  disparó y qué tendría que verse distinto.

Y una regla que cierra el circuito con el catálogo: **nunca inventa una
plantilla que no está en el documento.** Si falta, la pide. Eso saca de la lista
uno de los errores viejos —«escribir en notas.txt que una plantilla no existe
sin haber leído la lista»— porque la lista ya no es algo que haya que acordarse
de leer.

---

## 4. Lo que falta, y qué necesito para hacerlo

### Decisión tuya: el agente 363

El **363 (BOSS Padel)** es el que atiende de verdad, por WhatsApp. Hoy sigue
como estaba y no lo toqué, porque cambiarlo se le nota al cliente. Tres cosas
que convendría hacerle, y las tres son tu llamada:

1. **Que pueda delegar en el Diseñador.** El vínculo 363 → 364 existe pero está
   muerto (`toolName` y `toolDescription` en `null`). Darle nombre y descripción
   es lo que hace que el 363 pueda mandarle un pedido de diseño al 364.
2. **Asociarle el manual de marca (779).** Hoy el 363 no lo lee — lo lee el
   worker. Son dos verdades distintas para el mismo cliente.
3. **Asignarle `anotar_regla`.** O dejarla sólo en el Diseñador, que es donde
   más sentido tiene.

### El estudio

Lo que hay ahora deja publicar una plantilla nueva **editando dos archivos y
desplegando**. Falta lo que saca el despliegue del medio: que el motor lea las
plantillas de la base en vez del disco, y la pantalla para pedirlas y
corregirlas. Es la etapa 2 y 3 del plan, y ahora tienen sobre qué apoyarse.

### El cabo suelto de `americano`

`precio` desaparece si va vacío, y la regla del 12/8 dice que en los anuncios de
torneos siempre tiene que figurar el precio por pareja. Si un americano cuenta
como torneo, la corrección es una línea en `plantillas/americano/plantilla.json`.
Lo tiene que decir el club.
