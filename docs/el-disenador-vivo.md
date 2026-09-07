# El diseñador vivo

**Cómo hacer que el agente que hoy corre en Google Cloud se pueda entrenar desde
Asistime, y no sólo llamar para que haga una pieza.**

Escrito el 24 de agosto de 2026, sobre el traspaso del 12 de agosto.
Todo lo que dice «verificado» se leyó de la API de Asistime ese mismo día, no de
una pantalla ni de memoria.

---

## 0. Lo que encontré, verificado

Antes de proponer nada, lo que está pasando de verdad en el tenant 119:

| Qué | Estado real | Cómo se verificó |
|---|---|---|
| `anotar_regla` (tool 1725) | **Sigue sin asignar** al agente 363 | `GET /tenants/119/agents/363/tools` → devuelve 7 tools, y no está |
| Manual de marca (doc 779) | **No está asociado al agente 363** | `GET /tenants/119/agents/363/documents` → sólo el 739, «Sedes y Contactos» |
| Sub-agente 364 | Sigue vinculado con `toolName: null`, `toolDescription: null` | `GET /tenants/119/agents/363/sub-agents` |
| API_CLAVE de `api-disenos` | Está en texto plano en el código de 4 tools, visible para cualquiera que abra esa pantalla | leído en `crear_diseno`, `estado_diseno`, `publicar_diseno`, `estado_publicacion` |
| MCP servers en el tenant | Existen y funcionan (hay uno de Google Drive por Composio) | `GET /tenants/119/mcp-servers` |

Las dos primeras filas son hallazgos nuevos y el segundo no estaba en el
traspaso: **el agente que conversa con el club no lee el manual de marca.** Lo
lee el worker. Son dos verdades distintas para el mismo cliente: si mañana el
club anota «el americano sale $890», la pieza sale con $890 y el chat puede
seguir diciendo otra cosa.

---

## 1. El diagnóstico, en una frase

**Hoy el diseñador no es un agente: es una función.**

Hay dos cosas que en las conversaciones se llaman «el agente» y no son lo mismo:

- **BOSS Padel (363)** vive en Asistime. Conversa. Tiene prompt versionado,
  herramientas, documentos, simulador. Es entrenable — pero no sabe diseñar.
  Lo único que sabe hacer es **encargar**.
- **El diseñador** vive adentro del worker: `app/disenador.py` más
  `.claude/skills/boss-padel-disenos/`. Es el que realmente decide plantilla,
  foto, encuadre, jerarquía tipográfica y caption. Corre con el Agent SDK.
  **No existe en Asistime.** No tiene prompt versionado, no tiene evaluaciones,
  no tiene memoria de lo que le corrigieron ayer, y su criterio se cambia con un
  `git push`.

Por eso «entrenarlo desde Asistime» hoy alcanza a una parte chica: el manual de
marca. Todo el resto —cómo compone, qué prioriza, qué aprendió de la pieza que
salió mal el jueves— requiere despliegue.

Y hay algo peor que la falta de despliegue: **la corrección se pierde.** Cuando
alguien del club mira la placa y dice «el logo va más chico» o «esa foto no»,
ese dato no queda en ningún lado. La pieza siguiente arranca de cero y el club
repite la misma corrección cinco veces. Eso es exactamente lo que la gente
quiere decir cuando dice «quiero entrenarlo».

---

## 2. «Entrenar» son cuatro cosas distintas

Vale la pena separarlas porque cada una se arregla en un lugar diferente y tres
de las cuatro ya tienen dónde vivir.

| # | Qué se entrena | Ejemplo | Dónde vive hoy | ¿Entrenable desde Asistime? |
|---|---|---|---|---|
| 1 | **Datos** | «el americano sale $890» | Documento 779 | Sí ✅ |
| 2 | **Criterio** | «ante la duda, carrusel» | Documento 779 | Sí, pero sólo lo ve el worker ⚠️ |
| 3 | **Conducta** | «preguntá la sede antes de encargar» | Prompt del 363 / código del diseñador | El 363 sí. El diseñador **no** ❌ |
| 4 | **Corrección sobre una pieza** | «ese logo va más chico» | En ningún lado | **No existe** ❌ |

El (4) es el agujero. Es el que hace que el sistema se sienta muerto aunque
funcione perfecto: hace su trabajo, pero no aprende de él.

Y hay una quinta capa que conviene nombrar aunque no sea entrenable: **el
motor** —las 14 plantillas, dónde cae cada texto, los tamaños—. Eso se cambia
con código y está bien que así sea. La regla del traspaso sigue en pie: *si es
«qué decir o qué elegir» → manual; si es «cómo se ve» → motor.* Lo que agrego
es que entre esas dos hay dos capas más que hoy no tienen casa: la conducta del
diseñador y la memoria de correcciones.

---

## 3. La decisión de fondo: ¿el diseñador corre en Asistime o se entrena desde Asistime?

Son cosas distintas y conviene no confundirlas, porque una cuesta seis semanas
y la otra dos.

### Opción A — el diseñador corre adentro de Asistime

Se crea un agente «Diseñador» nativo, y el worker se convierte en un MCP server
que expone primitivas del motor: `listar_plantillas`, `renderizar`,
`buscar_foto`, `componer_video`.

- **A favor:** todo en un lugar. Prompt versionado, evaluaciones, simulador.
- **En contra, y pesa:** el diseñador hoy trabaja con el sistema de archivos.
  Escribe el HTML, lo renderiza, **mira el PNG que salió** y lo corrige. Ese
  bucle —ver el resultado y arreglarlo— es lo que hace que la pieza salga bien.
  Reemplazarlo por llamadas a herramientas sueltas lo rompe. Además el runtime
  de agentes de Asistime está pensado para chat, no para 2 a 4 minutos con
  Chromium y ffmpeg adentro.

### Opción B — el diseñador sigue corriendo en el worker, pero su cerebro se lee de Asistime

El worker **ya hace exactamente esto** con el manual de marca: en cada pieza lo
baja de Asistime (`app/manual.py`) y lo mete en el contexto. Lo que propongo es
extender ese mismo mecanismo a todo lo demás que hoy está en código.

- **A favor:** no se rompe nada. El bucle de render se conserva. El 90% del
  código ya existe. Se entrega en etapas, cada una sirve sola.
- **En contra:** el diseñador no «vive» literalmente en Asistime. Vive
  espejado. Pero **se entrena desde Asistime**, que es lo que se pidió.

### Recomendación: B ahora, con la puerta abierta a A

Lo que hace falta es que el club pueda cambiar cómo diseña sin esperar un
despliegue. Eso lo da la B. Ejecutarlo adentro de Asistime es una migración del
motor, no del cerebro, y hoy no compra nada que la B no compre.

La puerta queda abierta porque el paso 5 del plan (el MCP server) es el mismo en
las dos opciones. Si algún día conviene la A, la mitad ya está hecha.

---

## 4. La arquitectura propuesta

Cuatro capas, cada una con un dueño y una velocidad. Las dos del medio son
nuevas.

```
   ASISTIME  (lo que se entrena, sin desplegar nada)
   ┌──────────────────────────────────────────────────────┐
   │  Agente que atiende (363)                            │
   │    · prompt versionado          ← nosotros, minutos  │
   │    · doc 779 manual de marca    ← el club  ⚠ FALTA   │
   │                                                      │
   │  Agente Diseñador (nuevo)          ← NO conversa.    │
   │    · prompt versionado = la conducta del diseñador   │
   │    · doc: manual de marca (779)                      │
   │    · doc: APRENDIZAJES              ← nuevo          │
   │    · doc: catálogo del motor        ← lo escribe el  │
   │                                        deploy        │
   │    · suite de evaluaciones          ← la red         │
   └───────────────┬──────────────────────────────────────┘
                   │  el worker lo lee en cada pieza
                   │  (extiende manual.py → cerebro.py)
                   ▼
   ┌──────────────────────────────────────────────────────┐
   │  WORKER · Cloud Run Job        (lo que se despliega) │
   │    · el bucle de render con Chromium y ffmpeg        │
   │    · motor/ compartido + skills/<marca>/             │
   │    · avisa por push cuando termina        ← nuevo    │
   └───────────────┬──────────────────────────────────────┘
                   ▼
              Supabase  →  la app, el chat, Instagram
```

Cinco piezas nuevas. Ninguna reemplaza lo que hay: lo completan.

### 4.1 El espejo del cerebro (`cerebro.py`)

`app/manual.py` ya baja el documento 779 y lo mete en el contexto del diseñador,
y ya deja registro de qué versión usó en `metricas.manual`. Se extiende para
bajar también:

- el **prompt del agente Diseñador** (`GET /agents/{id}/prompt-versions`, la
  publicada);
- el documento de **aprendizajes**;
- el **catálogo del motor** (ver 4.4).

Cachea por número de versión: si el documento no cambió, no se vuelve a bajar ni
se paga el contexto de nuevo. Y `metricas` pasa a registrar las cuatro versiones,
no una. Cuando una pieza salga mal, se va a poder decir con qué cerebro exacto se
hizo.

Costo de contexto: hoy el 79% del gasto por pieza es contexto. Esto lo sube. Hay
que medirlo antes y después —está el instrumento, `costo-por-diseno.md`— y si
sube demasiado, la salida es resumir el catálogo del motor, no sacar el manual.

### 4.2 El documento de aprendizajes

Un documento nuevo en Asistime, hermano del manual, con una diferencia que
conviene respetar:

- **Manual de marca** = lo que el club dictó. «De ahora en más…». Lo escribe una
  persona con intención.
- **Aprendizajes** = lo que salió mal y se corrigió. Nace de una pieza concreta,
  con fecha, con el id del diseño, y con lo que se pidió cambiar.

Mezclarlos ensucia los dos. El manual tiene que poder leerlo el cliente de
principio a fin; los aprendizajes son un registro que crece rápido y del que el
diseñador levanta patrones.

### 4.3 `corregir_pieza` — el bucle que falta

Es la pieza más importante de todo esto y hoy no existe.

La persona ve la placa y dice «el logo va más chico». Una sola herramienta hace
tres cosas:

1. **Re-encola la pieza** con la corrección, referida al diseño original —no un
   pedido nuevo desde cero.
2. **Anota el aprendizaje** en el documento, con el id de la pieza y la fecha.
3. **Crea un caso de evaluación** (`POST /agent-evaluations`) con esa corrección
   como criterio.

El paso 3 es el que convierte una queja en entrenamiento. Una corrección deja de
ser un mensaje de WhatsApp y pasa a ser una regla más un test que la vigila.

### 4.4 La suite de evaluaciones

Asistime ya tiene el motor de evaluaciones: turnos de usuario más *assertions*
—`tool_called`, `text_contains`, `text_not_contains`, `llm_judge`— con
transcript por corrida. Es la red de seguridad que hoy no hay.

Casos que salen directo de las trampas del traspaso:

| Caso | Assertion |
|---|---|
| «una placa para el torneo del 28» | `tool_called: crear_diseno` |
| «de ahora en más no uses somospadel» | `tool_called: anotar_regla` |
| «quiero el hashtag pegado al borde de abajo» | `tool_called: avisar_cambio_motor` |
| mientras la pieza no está lista | `text_not_contains` de una URL de storage — que no invente el link |
| cualquier caption entregado | `llm_judge`: «cierra con una pregunta o un pedido de comentario» |

Regla de operación: **antes de publicar una versión nueva del manual o del
prompt, corre la suite.** Es lo que permite tocar sin miedo, que es la condición
para que el cliente toque de verdad.

Ojo con lo que ya sabemos: el simulador no simula las herramientas, las ejecuta.
Los casos de evaluación que disparan `crear_diseno` van a generar y a cobrar
piezas de verdad (~US$0,70). O se acepta el costo de la suite, o los casos de
diseño usan un pedido marcado como prueba que el motor reconozca y corte antes
de renderizar. Recomiendo lo segundo.

### 4.5 El MCP server del motor

Las cuatro herramientas `custom_code` que hablan con las Edge Functions se
reemplazan por un MCP server. Asistime lo soporta nativo: `streamable_http`,
autenticación por headers con `isSecret: true`, y `POST /mcp-servers/{id}/sync`
para descubrir las herramientas.

Qué compra:

- **Paga la deuda de seguridad #3 de raíz.** La clave deja de estar pegada en el
  código de cuatro tools, a la vista de cualquiera que abra esa pantalla, y pasa
  a estar guardada como secreto. Es la regla del traspaso aplicada en serio: el
  secreto deja de vivir en un lugar que no controlamos.
- **Un cliente nuevo deja de ser copy-paste de JavaScript.** Hoy dar de alta a
  Clínica significa duplicar cuatro tools cambiando la URL y la clave a mano —y
  el traspaso ya documenta que un secreto pegado a mano en dos lugares siempre
  termina difiriendo.
- **Es el paso que también sirve para la opción A**, si algún día se elige.

---

## 5. Lo que hace que se sienta vivo: dejar de preguntar

Aparte de entrenarlo, hay un cambio chico con efecto grande.

Hoy el agente encarga y después **pregunta**: `estado_diseno` se queda bloqueada
hasta 100 segundos y, si no llegó, vuelve a preguntar. Funciona, pero la
conversación se siente en pausa.

Asistime tiene `POST /tenants/{id}/inboxes/{inboxId}/messages/send`. El worker
puede **avisar** cuando terminó, en la conversación, sin que nadie pregunte. La
pieza aparece sola.

Es el cambio de menor costo y mayor efecto percibido de toda esta lista. Antes de
comprometerse hay que medir una cosa: si ese endpoint sirve para el canal web de
Lovable o sólo para WhatsApp. Es media hora de prueba.

---

## 6. El plan, por etapas

Cada etapa entrega valor sola. Ninguna depende de que la siguiente exista.

**Etapa 0 — las tres claves.** Sigue siendo lo más urgente y no cambió desde el
12 de agosto: la key de Anthropic filtrada, la `service_role` de Boss impresa en
una terminal, y la `API_CLAVE` de `api-disenos`. Antes que cualquier otra cosa de
este documento. La etapa 5 hace que la tercera no vuelva a pasar, pero no rota la
que ya está expuesta.

**Etapa 1 — cerrar lo que quedó abierto (medio día).**
Asignar `anotar_regla` al 363 y verificarlo releyendo, no por lo que devuelva la
escritura. Asociar el documento 779 al agente 363 —es el hallazgo nuevo—. Jubilar
o arreglar el sub-agente 364. Preguntarle a Bruno si le llegaron los avisos.

**Etapa 2 — la devolución por push (2 a 3 días).**
El worker avisa en la conversación cuando la pieza está. El sistema deja de
sentirse en pausa.

**Etapa 3 — el bucle de entrenamiento (1 semana).**
Documento de aprendizajes, `corregir_pieza`, y el espejo del cerebro leyendo los
dos documentos. Acá es donde «entrenar desde Asistime» pasa a ser cierto.

**Etapa 4 — la red de seguridad (3 a 4 días).**
Suite de evaluaciones con los cinco casos de arriba, más el mecanismo de pedido
de prueba para no pagar renders en cada corrida. Regla: la suite corre antes de
publicar.

**Etapa 5 — el MCP server del motor (1 semana).**
Reemplaza las cuatro `custom_code`. Cierra la deuda de secretos y hace que el
cliente número tres no sea copy-paste.

Lo del renglón fijo al pie de las stories —el primer pedido real que entró por el
aviso de motor y que sigue sin hacerse— es motor, no entra en este plan, y
conviene hacerlo igual porque lleva horas y es el único pedido que el sistema
tomó y no cumplió.

---

## 7. Los tres riesgos, y cómo se miden antes de comprometerse

No son objeciones: son las tres cosas que hay que medir en la primera semana,
porque cualquiera de las tres cambia el plan.

1. **El contexto sube y el costo con él.** Sumar tres documentos al prompt del
   diseñador engorda la parte que ya es el 79% del gasto. *Medir:* generar diez
   piezas con el cerebro espejado y comparar contra las diez de referencia. Si el
   costo por pieza pasa de ~US$1,10, se resume el catálogo del motor.
2. **El push puede no servir para el canal web.** *Medir:* mandar un mensaje por
   `inboxes/{inboxId}/messages/send` a una conversación de Lovable. Si no llega,
   la etapa 2 se hace del lado de Supabase con realtime y no del lado de
   Asistime.
3. **Las evaluaciones ejecutan herramientas de verdad.** *Medir:* correr un caso
   que dispare `crear_diseno` y confirmar que el pedido de prueba corta antes de
   renderizar. Si no corta, cada corrida de la suite cuesta plata real y hay que
   acotar cuántos casos disparan diseño.

Y la trampa que ya nos costó dos tardes, que aplica a todo lo de arriba:
**verificá el estado, no tu intención.** Ninguna de estas etapas se da por hecha
porque una pantalla o una respuesta de la API digan que sí. Se relee después.

---

## 8. Lo que hay que decidir antes de arrancar

Tres preguntas. Ninguna la puedo contestar yo.

1. **¿Dónde vive el proyecto nuevo?** Este repo (`calculadora-asistime`) está
   vacío y el nombre no dice nada de esto. ¿Repo nuevo, o se renombra este?
2. **¿A o B?** Mi recomendación es B —espejar el cerebro— y está argumentada en
   la sección 3. Si la idea es que el diseñador ejecute adentro de Asistime, el
   plan es otro y es bastante más largo.
3. **¿Este proyecto es el producto multi-cliente o es el de Boss?** Cambia dónde
   viven los documentos: uno por tenant, o un documento base compartido más un
   documento por marca. La respuesta importa recién cuando llegue el cliente
   número tres, pero la estructura se define ahora.
