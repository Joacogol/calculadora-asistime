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

## 4. Asistime · el circuito quedó conectado

El **363 (BOSS Padel)** es el que atiende de verdad por WhatsApp. Se le hicieron
dos cambios, los dos verificados releyendo:

**Ahora puede derivar en el Diseñador.** El vínculo 363 → 364 existía desde
agosto pero estaba muerto: `toolName` y `toolDescription` en `null`. Ahora tiene
nombre —`disenador`— y una descripción que dice cuándo derivar y cuándo no:

> Derivá acá cuando alguien pide una pieza […] También cuando pide que algo
> cambie de ahora en más: un precio o un horario nuevo, una regla de qué foto
> usar o qué no decir, o que una plantilla se vea distinta. […] **No derives acá
> reservas de cancha, precios de alquiler ni consultas de horarios libres: eso
> lo contestás vos.**

El sub-agente no ve la conversación, así que la descripción le pide
explícitamente al 363 que le pase el contexto entero. Es el error más fácil de
cometer con una delegación y el más difícil de diagnosticar después.

**Ahora lee el manual de marca.** Se le asoció el documento 779, que antes sólo
leía el worker. Era el hallazgo de la primera lectura: si el club anotaba «el
americano sale $890», la pieza salía bien y el chat podía seguir diciendo otra
cosa. Eso se terminó.

Quedó con sus dos documentos: Sedes y Contactos (739) y Reglas de marca (779).

### El circuito completo, hoy

```
  el club escribe por WhatsApp
            ↓
  BOSS Padel (363)  ── reservas, horarios, sedes → contesta él
            │
            └─ disenador ──→  Diseñador (364)
                                ├── Catálogo de plantillas (831)  ← lo genera el motor
                                ├── Reglas de marca (779)         ← lo edita el club
                                │
                                ├── crear_diseno · estado_diseno
                                ├── publicar_diseno · estado_publicacion
                                ├── anotar_regla         ← «qué decir o qué elegir»
                                └── avisar_cambio_motor   ← «cómo se ve»
```

---

## 5. La base toma el mando · el despliegue sale del medio

Esta es la parte que faltaba para que «publicar una plantilla» no sea
«desplegar el worker».

**La tabla existe en el Supabase de Boss.** `plantillas`, versionada: cada fila
es una versión con su HTML, su contrato, quién la subió y qué cambió. Dos cosas
que vale la pena mirar:

- Un índice único parcial hace que **no puedan existir dos versiones publicadas
  de la misma plantilla**. No es una regla que alguien tenga que recordar: es
  imposible. Sin eso, el worker levantaría dos filas para el mismo slug y cuál
  gana dependería del orden en que vuelvan — la clase de bug que aparece una
  vez cada tres semanas.
- El número de versión lo calcula la base, no quien llama. Si lo calculara el
  cliente —leer el máximo, sumar uno, escribir— dos guardados simultáneos
  pedirían la misma versión y uno se perdería.

**El worker las baja al skill en cada corrida.** `app/plantillas.py`, en el
mismo lugar y con la misma forma que el banco de fotos: sólo si hay algo que
diseñar, y si falla se sigue.

Escribe archivos en vez de devolver un diccionario, y eso es deliberado: el
diseñador no es una función que reciba parámetros, es un agente con el sistema
de archivos delante — escribe el spec, corre `render.py`, mira el PNG y lo
corrige. Bajando los archivos, para el resto del sistema una plantilla que vino
de la base y una que vino del despliegue son la misma cosa. Ni el agente, ni
`render.py`, ni el generador de catálogo se enteran.

**Nunca borra.** Lo que está en la base pisa lo del disco; lo que no está en la
base se queda como vino. Si borrara, un cliente que todavía no corrió
`plantillas.sql` se quedaría sin ninguna plantilla y sin forma de diseñar,
cuando las del despliegue estaban ahí y andaban.

### Verificado de punta a punta

Contra una base de prueba —creada, usada y borrada— con el cliente HTTP real:

| Prueba | Resultado |
|---|---|
| Borrar `tip` del disco y correr la corrida | vuelve de la base, mismo MD5 |
| Renderizar las 14 con `tip` viniendo de la base | **56 / 56 idénticos** |
| Correr la sincronización dos veces | la segunda no toca el disco |
| Una base sin la tabla (el caso de Clínica) | log informativo, sigue con las del despliegue |
| Una base que no contesta | warning, sigue con las del despliegue |

En la base de Boss quedó `tip` publicada como versión 1. Las otras once las
sube `herramientas/sembrar-plantillas.py` en un comando, con las mismas claves
que usa el worker.

---

## 6. El estudio · la pantalla existe y anda

Un servicio chico al lado del worker. Tres paneles: las plantillas de la marca,
el diseño, y la pieza — con los cuatro formatos a un clic.

**El preview es la pieza. No se le parece: es la misma.**
`motor.plantillas.compilar()` —la función que usa el estudio— es literalmente la
que arma la pieza que sale a Instagram. Para que eso no fuera una promesa que
alguien tiene que mantener, el motor se refactorizó: hay **una sola función** que
arma una página, y la usan las dos.

Medido: las 12 plantillas en sus 4 formatos, renderizadas por el estudio y por
el motor de producción con los mismos datos, comparadas por MD5.

```
48 / 48 idénticos
```

Un preview que dibuja por otro lado se ve bien en el editor y sale distinto en
la pieza. A partir de ahí nadie vuelve a confiar en lo que ve, que es lo único
que hace que un editor sirva para decidir.

### Tres cosas que salieron de mirar cómo se trabaja

**Los datos de prueba se llenan solos**, del contrato. Pedirle al diseñador que
invente doce campos antes de ver nada es la forma más rápida de que cierre la
pestaña. Y un campo cuyo valor por defecto es vacío **se muestra vacío**:
`contacto` en `torneo` es justo eso —la marca dice que el teléfono no va salvo
que lo pidan— y un preview que lo inventa enseña lo contrario de lo que hay que
aprender.

**Romper algo es el estado normal** mientras alguien edita, no una excepción. El
error vuelve como texto legible al lado del preview, con el número de línea
cuando Jinja lo sabe, en vez de un 500 que deja la pantalla en blanco.

**Publicar pide una etiqueta.** No es burocracia: es lo que se va a leer dentro
de seis meses cuando haya que entender por qué la pieza salió así.

### Un error que valía la pena cometer

La primera versión guardaba el navegador con un candado alrededor. Falló con
«Cannot switch to a different thread»: Playwright ata el navegador al hilo que
lo creó, y el servidor atiende cada pedido en uno distinto. Un candado no
alcanzaba porque el problema no era que entraran dos a la vez, era que entrara
*otro*. Ahora el navegador vive en su propio hilo y recibe trabajo por una cola
— que además da gratis lo que el candado buscaba.

---

## 7. Lo que falta

### La primitiva de grilla

`duelo` y `horarios` vuelven a ser datos recién cuando su lógica de composición
suba a `motor/`. Hasta entonces, esas dos se siguen cambiando con despliegue.

### El cabo suelto de `americano`

`precio` desaparece si va vacío, y la regla del 12/8 dice que en los anuncios de
torneos siempre tiene que figurar el precio por pareja. Si un americano cuenta
como torneo, la corrección es una línea en `plantillas/americano/plantilla.json`.
Lo tiene que decir el club.

### Las claves, que siguen igual

Trabajando en el tenant se vio de nuevo: la misma `API_CLAVE` está pegada en
texto plano en el código de tres tools, y una segunda clave en el código de
`anotar_regla`. Cualquiera que abra esa pantalla las ve. Sigue siendo lo más
urgente del proyecto y no lo resuelve nada de lo que se hizo hoy.

---

## 8. Cómo probarlo

Simulador → agente **Diseñador Boss Padel**. Ojo con lo de siempre: el simulador
no simula las herramientas, las ejecuta. Un pedido de diseño genera y cobra una
pieza de verdad (~US$0,70).

Tres frases que prueban las tres puertas:

| Escribí | Tiene que llamar a |
|---|---|
| «de ahora en más no uses la frase somospadel. No me hagas ninguna pieza ahora.» | `anotar_regla` |
| «quiero una plantilla para las clases, con el profe y el horario. No me hagas ninguna pieza ahora.» | `avisar_cambio_motor` |
| «¿qué plantillas tenés?» | ninguna — lo contesta leyendo el catálogo |

La tercera es la que verifica que el catálogo llegó: tiene que nombrar las 14 y
no inventar ninguna.

Y desde el 363, para probar la derivación: «necesito una placa para el torneo
del 28 en Carrasco» tiene que pasar por `disenador`, no resolverse ahí.
