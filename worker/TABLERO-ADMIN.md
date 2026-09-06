# Tablero de administración: qué consume, qué genera y cuánto se cobra por cliente

Documento de diseño. No hay código todavía: esto es para pensarlo antes de
construirlo. Todo lo que dice «hoy» sale del código del worker y de las bases
reales, no de supuestos.

## 1. Qué se registra hoy y qué falta

El worker deja rastro de todo lo que hace, pero en cuatro lugares distintos y
con cuatro unidades distintas. Y el cobro sólo mira uno de los cuatro.

| Qué produce | Dónde queda | Qué costo guarda | ¿Se cobra? |
|---|---|---|---|
| Placas (diseños) | `disenos.metricas` | `costo_usd` real del SDK, tokens, `segundos`, `turnos`, `modelo` | **Sí**: `cobro.registrar` desde `chat.py`, con `MARGEN` |
| Reels y videos | `reels.metricas.costo` | `{monto, moneda}` — `usd` (fal.ai) o `creditos` (Magnific) | **No** |
| Fotos editadas | `fotos_editadas` | `creditos_estimados` / `creditos_gastados` (Magnific) | **No** |
| Publicaciones en IG | `publicaciones` | nada (no cuesta) | — |

Y lo que está alrededor:

- **Cobro sólo en dos clientes.** `movimientos` + la vista `mi_cuenta` existen en
  Boss y Clínica. Stadium y Asistime no tienen tablas de cobro: `saldo()`
  devuelve `None` y el worker trabaja gratis a propósito (regla de `cobro.py`).
- **El margen vive en una variable de entorno.** `MARGEN=2.0` global en
  `desplegar-chat.sh:375`. El mecanismo por cliente (`MARGEN_<MARCA>`) existe
  en código pero nadie lo usa. Cambiar el margen de un cliente hoy es
  redesplegar Cloud Run.
- **Una base por cliente, ningún libro central.** Para saber cuánto gastaste
  este mes hay que abrir cuatro Supabase y sumar a mano.
- **La infraestructura no se atribuye a nadie.** Cloud Run, Supabase, el
  bucket: se pagan en bloque. Pero `metricas.segundos` existe por pieza, así
  que hay con qué repartirlo.

Con números de Boss (el cliente con más historia):

| | |
|---|---|
| Consumos registrados | 50 |
| Costo API acumulado | US$ 28,31 |
| Cobrado (×2) | US$ 56,64 |
| Cargas | US$ 60,00 |
| Saldo | US$ 3,36 |
| Reels hechos sin cobrar | 20 |
| Fotos editadas sin cobrar | 4 |
| Agosto: piezas / costo / promedio | 47 / US$ 26,75 / US$ 0,569 |
| Agosto: minutos de worker | 75 |

Los 20 reels son la fuga más grande: cada uno le costó a Asistime dólares de
fal.ai o créditos de Magnific y ninguno pasó por `cobro`.

## 2. Tres tipos de costo, tres tratamientos

No todo lo que cuesta se cobra igual. Mezclarlos en un solo número es lo que
hace que un tablero «completo» termine mintiendo.

1. **Costo directo en dólares que paga Asistime.** Anthropic (placas), fal.ai
   (reels). Es el único que tiene sentido multiplicar por un margen. Hoy sólo
   Anthropic pasa por `cobro`.
2. **Créditos de Magnific.** Se descuentan de una cuenta. Si la cuenta es del
   cliente, no se cobra: se **muestra** (consumo, tope, cuánto le queda) para
   que él sepa por qué se le acabó. Si la cuenta es de Asistime, es un costo
   directo más y va por el punto 1 con un precio por crédito.
3. **Infraestructura compartida.** Cloud Run, Supabase, almacenamiento, tu
   tiempo de alta. No se factura por pieza. Se reparte para saber el margen
   *real* de cada cliente, que es distinto del margen sobre la API. `cobro.py`
   lo avisa en su propio docstring: «el margen sobre la API es sólo una parte».

El tablero muestra los tres por separado y recién al final los junta en una
línea que se llame por su nombre: **margen efectivo**.

## 3. Arquitectura de datos: un libro central

Lo que hace posible el tablero es una sola tabla, en una sola base, que el
worker escriba cada vez que termina algo. Todo lo demás son vistas sobre ella.

**Dónde vive.** En el Supabase de Asistime (`qxjvtxumkljsroukpkny`), que ya es
la casa. No en el de ningún cliente: el cliente no tiene por qué ver los
costos de los demás ni tu margen.

**La tabla `libro`.** Una fila por evento con costo:

```
marca             boss-padel-disenos
tipo              placa | reel | video | foto | publicacion
pieza_id          el id en la base del cliente
proveedor         anthropic | fal | magnific | instagram
modelo            claude-… / kling-… / …
costo_usd         lo que pagó Asistime (0 si fue con créditos del cliente)
creditos          créditos de Magnific gastados (0 si no aplica)
cuenta_creditos   cliente | asistime
segundos          duración del trabajo del worker
tokens_entrada, tokens_salida, cache_lectura, cache_escritura
precio_usd        lo que se le cobró al cliente
margen_aplicado   el multiplicador que se usó en ese momento
cobrado_en        movimientos.id en la base del cliente, o null si no se cobró
creado
```

Guardar `margen_aplicado` por fila es lo que permite cambiar el margen mañana
sin reescribir la historia.

**La tabla `clientes`.** Reemplaza la variable de entorno:

```
marca, nombre, supabase_ref, margen, moneda_factura (USD|UYU),
tope_usd_mes, precio_credito_usd (null si los créditos son del cliente),
cobra (bool), activo
```

El worker la lee al arrancar cada ciclo y cae a `MARGEN` del entorno si no
puede leerla, con el mismo criterio de `saldo()`: un error de red no frena la
producción.

**Lo que queda en cada cliente.** `movimientos` y `mi_cuenta` siguen siendo el
estado de cuenta *del cliente*: lo que él ve. El libro central es lo que ves
vos. La regla es que cada fila de `libro` con `precio_usd > 0` tiene su fila
espejo en el `movimientos` del cliente, y el tablero avisa cuando no la tiene
(un consumo que `registrar` no pudo anotar, que hoy sólo queda en el log).

## 4. Cambios en el worker antes de cualquier pantalla

El tablero no puede mostrar lo que nadie escribe. Esto va primero:

1. **`cobro.registrar` escribe en dos lados**: el `movimientos` del cliente y
   el `libro` central. Si falla el central, se loguea y sigue: el cliente ya
   tiene su pieza y su cargo.
2. **Reels y videos pasan por `cobro`.** En `reelero.py`, donde ya se guarda
   `metricas.costo`, se llama a `registrar` con el monto en dólares. Si la
   moneda es `creditos`, se escribe en `libro` con `costo_usd = 0` y
   `creditos = N`, y se cobra sólo si `precio_credito_usd` está cargado para
   esa marca.
3. **Fotos editadas, igual**, desde `fotero.py`, con `creditos_gastados`.
4. **Margen desde `clientes`**, con el entorno como respaldo.
5. **`cobro.sql` en Stadium**, y decidir si Asistime (tu propia cuenta) lleva
   cobro o sólo libro. Recomendación: sólo libro, con `cobra = false`. Así ves
   cuánto te cuesta producir tu propio contenido sin cobrarte a vos mismo.
6. **Carga retroactiva del libro** con un script de una vez que lea
   `disenos`, `reels` y `fotos_editadas` de las cuatro bases. Sin esto el
   tablero arranca en cero y los 50 consumos de Boss quedan afuera.

## 5. El tablero, sección por sección

Es una herramienta que se escanea, no un documento que se lee. Lo urgente
arriba, el detalle abajo, y cada número con su unidad al lado.

### Resumen (la pantalla de entrada)

Mes en curso, con el anterior al lado para comparar.

- Costo total, cobrado, margen bruto en dólares y en porcentaje.
- Piezas por tipo: placas, reels, fotos, publicaciones.
- Ranking de clientes por costo y por margen. El que más gasta no es
  necesariamente el que más deja.
- **Alertas**, con forma y no sólo número: saldo por debajo del piso,
  token de Instagram que vence en menos de diez días, consumos sin espejo
  en `movimientos`, errores del worker en las últimas 24 horas, pedidos
  atascados en `pendiente`.

### Por cliente

Una pantalla por marca, **vestida con la identidad de esa marca**: logo,
tinta, acento y fondo salen de su `marca.json` (en los kits por datos) o de
`brand` en el worker (Boss y Clínica, hasta que migren). No es decoración:
cuando abrís Stadium tiene que sentirse Stadium para que no confundas a quién
le estás mirando la cuenta.

- Saldo actual y cuántas piezas «le quedan» al costo promedio del mes.
- Consumo del mes por tipo, con costo, precio y margen en cada fila.
- Costo vs. cobrado en el tiempo (área, un mes por punto).
- **Margen efectivo**: cobrado menos costo directo menos su parte de
  infraestructura.
- Galería de las últimas piezas con enlace, plantilla usada, avisos del
  motor y si fue corregida (`corrige`).
- Libro de movimientos: cargas, abonos, consumos, ajustes. Con el botón de
  cargar saldo acá mismo (hoy es `cobro.cargar` a mano).
- Estado de cuenta exportable (CSV y PDF) para mandarle al cliente.
- Instagram: cuenta conectada, vencimiento del token, últimas publicaciones.
- Configuración de la marca: margen, tope mensual, moneda, precio por crédito.

### Piezas

Una tabla cruzada de todos los clientes, con filtros por marca, tipo, fecha,
plantilla y modelo. Columnas: cliente, tipo, plantilla, modelo, turnos,
tokens, segundos, costo, precio, avisos del motor, corregida, publicada.
Es donde se descubre que una placa costó cuatro veces el promedio porque el
agente dio doce vueltas, y que una plantilla siempre dispara el mismo aviso.

### Infraestructura

Lo que no es por pieza: Cloud Run, Supabase, almacenamiento, Anthropic total
de la factura (para cruzar contra la suma del libro), fal.ai, Magnific.
Se carga a mano por mes al principio; la exportación de facturación de
Google a BigQuery puede alimentarlo después. Se reparte entre clientes por
`segundos` de worker y aparece como una línea en cada cliente.

### Facturación

- Cierre mensual por cliente: consumo, saldo, lo que hay que facturar.
- Conversión a pesos al tipo de cambio del día del cierre, si la moneda de
  factura es UYU. El libro siempre queda en dólares.
- Registrar cargas y abonos, y que eso escriba en el `movimientos` del
  cliente y en el libro.
- Histórico de cierres.

### Salud del sistema

Último ciclo del worker por cliente, pendientes atascados, errores recientes,
versión del catálogo y del prompt publicados, versión de `api-disenos` en
cada Supabase, tokens de Instagram. Es la sección que reemplaza los grep que
hacemos hoy después de cada deploy.

### Configuración

La tabla `clientes` editable: dar de alta una marca, cambiar su margen,
ponerle un tope, marcar si cobra. Cada cambio queda con fecha y quién lo
hizo.

## 6. Dónde construirlo

Tres opciones, con recomendación:

- **Panel de Asistime, como tool del tenant.** Es lo que ya usa el cliente.
  Pero el panel es por tenant y este tablero es cruzado: verías cuatro
  paneles, no uno. Descartado para la vista de administración.
- **App aparte** (Vite o Next en Vercel), leyendo el Supabase de Asistime con
  login sólo para vos, y con RLS para que la tabla `libro` no se lea sin
  sesión. **Recomendado.** Es un frontend chico sobre vistas SQL; lo pesado
  está en la base.
- **Lovable**, como la landing. Sirve para el prototipo visual, pero la
  lógica de vistas y el login conviene tenerlos en el repo.

## 7. Decisiones que son tuyas

1. **Base del precio.** Hoy es margen sobre la API: el cliente paga el doble
   de un costo que él no controla y que varía por pieza entre US$ 0,30 y
   1,40. La alternativa es **precio fijo por tipo** (placa, reel, foto) que
   se revisa cada mes contra el costo real del libro. Recomendación: precio
   fijo. Es lo que un cliente entiende y lo que se puede publicar en la
   landing; el margen sobre la API queda como el número interno que vigila
   el tablero.
2. **Moneda.** Libro en dólares, factura en la que el cliente pague. Falta
   decidir si el saldo que ve el cliente se muestra en pesos.
3. **Los reels ya hechos.** Boss tiene 20 reels sin cobrar. Cobrarlos
   retroactivamente es un `ajuste` que hay que explicarle; no cobrarlos es
   asumir la pérdida. Decisión comercial, no técnica.
4. **Vista del cliente.** Primera versión sólo para vos. `mi_cuenta` ya es lo
   que el cliente ve; una pantalla suya con la misma identidad puede venir en
   una segunda etapa.
5. **Créditos de Magnific.** ¿La cuenta es siempre del cliente, o hay marcas
   que usan la tuya? Eso decide `precio_credito_usd` por marca.

## 8. Orden de construcción

| Etapa | Qué incluye | Toca |
|---|---|---|
| 0. Datos | `libro`, `clientes`, `cobro` en dos lados, reels y fotos por `cobro`, `cobro.sql` en Stadium, carga retroactiva | `cobro.py`, `chat.py`, `reelero.py`, `fotero.py`, `desplegar-chat.sh`, SQL en Asistime y Stadium |
| 1. Tablero | Resumen, Por cliente, Piezas, sobre vistas SQL | app nueva + vistas |
| 2. Plata | Facturación, Infraestructura, cargas desde el tablero | app + `libro` |
| 3. Operación | Salud del sistema, Configuración editable | app + `clientes` |

La etapa 0 se puede desplegar sola y ya rinde: desde el primer ciclo con el
libro escrito, sumar el mes es un `select`.

## 9. Lo que el tablero no va a hacer

- No corta el servicio: eso sigue siendo `puede_generar` en el worker, del
  lado del servidor, como hasta ahora.
- No calcula costos que el worker no midió. Si una pieza no tiene
  `metricas`, aparece como «sin costo medido», no como cero.
- No muestra el margen al cliente. El multiplicador no sale de la casa.
