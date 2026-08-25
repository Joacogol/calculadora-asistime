# Desplegar el worker

Para quien va a correr los comandos. Si no sos vos, pasale esta página entera.

Hace falta: acceso a `gcloud` en el proyecto **boss-padel-disenos**, y acceso al
SQL Editor del Supabase de Boss. Nada más.

Todo esto ya corrió antes: el worker está desplegado desde agosto y esto es una
actualización, no una instalación. Los pasos 3 y 4 son los únicos que no se
hicieron nunca.

---

## Antes de empezar: qué es esto y por qué importa

El worker es un **Cloud Run job**: arranca, vacía la cola de pedidos, y
termina. Un reloj lo enciende **una vez por minuto**. No hay ningún proceso
que mantener vivo, así que no hay nada que se pueda "caer".

Lo que trae esta actualización, en una línea: **desde el chat de Asistime se
pueden pedir plantillas nuevas y correcciones de diseño, y salen solas en
minutos** — sin que nadie toque código ni despliegue nada.

---

## 1 · Traer el código y verificar que no rompe nada

```bash
cd /ruta/al/repo/del/worker
git pull
pip install jinja2
```

### Sobre la verificación

Hay una herramienta nueva, `verificar-motor.py`, que dibuja todas las
plantillas y avisa si un cambio movió alguna. **Para ESTE despliegue no se
puede usar**, y conviene entender por qué antes de saltearla:

esta actualización pasa las plantillas de estar escritas en Python a ser datos
—HTML + un contrato—. La herramienta sólo sabe dibujar las nuevas, así que no
hay contra qué comparar. La equivalencia de esa migración **ya se verificó
cuando se hizo**, con la misma regla y a mano: 56 renders, byte por byte
idénticos. Está documentado en `APLICAR.md`.

Para el despliegue siguiente y todos los que vengan, sí:

```bash
python3 herramientas/verificar-motor.py boss-padel-disenos --grabar   # ANTES
git pull
python3 herramientas/verificar-motor.py boss-padel-disenos --comparar # DESPUÉS
```

Tiene que decir `120 / 120 idénticas` y tarda unos 150 segundos. Si dice
`DISTINTA`, pará: esa actualización cambia una pieza que ya se estaba usando.
Las imágenes de antes y después quedan en `/tmp/verificar-motor/`.

Para éste, la verificación es la prueba de humo del final.

---

## 2 · Desplegar

```bash
./desplegar-chat.sh
```

Tarda unos minutos (compila la imagen). Va a pedir claves sólo si falta alguna
en Secret Manager; si ya están, no pregunta nada.

Hace cuatro cosas y las va cantando:

| Paso | Qué |
|---|---|
| 1/4 | los secretos de cada cliente (la `service_role` de su Supabase) |
| 1b/4 | la clave de la API de Asistime — **ver la nota de abajo** |
| 2/4 | despliega el job |
| 3/4 | el reloj: una corrida por minuto |

Termina con `▸ 4/4 Listo — clientes: boss-padel-disenos, …`.

> **Si pregunta por la clave de Asistime, no la dejes vacía.** Sin ella el
> worker diseña sin el manual de marca — o sea que las reglas que el club
> escribió desde el chat (precios, qué foto usar, el tono) **no se aplican**.
> Se despliega igual y no se nota hasta que sale una pieza con el precio viejo.

---

## 3 · Las tablas nuevas — una sola vez

En el **SQL Editor del Supabase de Boss**, pegar y ejecutar, en este orden:

1. `plantillas.sql` — las plantillas versionadas
2. `plantilla-pedidos.sql` — la cola de pedidos de plantilla
3. `motor-pedidos.sql` — la lista de pedidos que necesitan código

Los tres se pueden correr aunque ya existan: traen `if not exists` y
`add column if not exists`, así que no rompen nada si se repiten.

---

## 4 · Sembrar las plantillas — una sola vez

Sube al Supabase las plantillas que hoy viven sólo en el despliegue, para que
se puedan corregir desde el chat sin volver a desplegar.

```bash
python3 herramientas/sembrar-plantillas.py boss-padel-disenos --probar
python3 herramientas/sembrar-plantillas.py boss-padel-disenos
```

El primero no escribe nada: muestra qué haría. Corré el segundo sólo si lo que
lista tiene sentido.

Usa las mismas variables de entorno que el worker, así que tiene que correr con
el mismo entorno cargado.

---

## 5 · Republicar el catálogo

```bash
ASISTIME_CLAVE=… python3 herramientas/publicar-catalogo.py boss-padel-disenos
```

Es lo que le cuenta al agente qué plantillas existen. Es idempotente: si el
catálogo no cambió, no escribe una versión nueva. **Conviene dejarlo al final
de `desplegar-chat.sh`** para no tener que acordarse.

---

## Verificar que quedó andando

```bash
gcloud run jobs execute boss-chat --region southamerica-east1 --wait
```

Tiene que terminar sin error. En el log vas a ver
`worker arriba · N cliente(s)` y, si no hay nada en la cola,
`sin diseños pendientes, plantillas ni publicaciones en cola`.

Y la prueba de verdad, desde el chat de Asistime:

> «Necesito poder anunciar los cumpleaños en el club: el nombre, la edad y la
> fecha.»

En unos ocho minutos tiene que volver con un preview. Si a los quince no
volvió, mirá el log del job.

---

## Lo que NO hace este despliegue

- **No publica ninguna plantilla.** Las que se armen quedan como borrador hasta
  que una persona las apruebe desde el chat.
- **No prende el motorista.** Los pedidos que necesitan código quedan anotados
  en `motor_pedidos`, pero nadie los atiende. Para prenderlo hay que agregar
  `MOTORISTA=1` a las variables del job — y conviene no hacerlo hasta que haya
  alguien mirando las propuestas.

---

## Dos cosas pendientes que no son de este despliegue

**Rotar tres claves.** La de Anthropic (`anthropic-key` en Secret Manager), la
`service_role` de Boss, y la `API_CLAVE` de las Edge Functions.

> **Cuidado con el orden de `API_CLAVE`.** Está escrita en texto plano dentro
> del código de **ocho herramientas de Asistime** —`crear_diseno`,
> `estado_diseno`, `publicar_diseno`, `estado_publicacion`, `crear_plantilla`,
> `estado_plantilla`, `publicar_plantilla` y `avisar_cambio_motor`—. Si se
> cambia el secreto antes de actualizarlas, **se caen las ocho a la vez**.
>
> El orden es: primero las herramientas con la clave nueva, después el secreto.
>
> Y para no confiar en esta lista, que puede quedar vieja: la forma segura de
> encontrarlas todas es buscar los primeros caracteres de la clave actual
> (`705fdf`) en el código de las herramientas del tenant 119.
>
> **`anotar_regla` usa otra clave** (`api-manual`, empieza con `1fe96e`). Es un
> secreto distinto y se rota aparte.

**El disparador.** Existe un servicio (`disparador/`) que enciende el job en el
instante en que entra un pedido, en vez de esperar el minuto. No está
conectado, y no es un olvido: la política de la organización bloquea el webhook
—está anotado en `desplegar-chat.sh`—. Si esa política cambia, se conecta con
`./desplegar-disparador.sh` y el hook que ese script imprime al final.

---

## Si algo sale mal

| Síntoma | Qué mirar |
|---|---|
| `verificar-motor` dice `DISTINTA` | esta actualización cambia una pieza que ya se usaba. Pará y avisá |
| El job falla al desplegar | casi siempre es un secreto que falta; el script dice cuál |
| Un pedido queda `pendiente` para siempre | el reloj no está corriendo: `gcloud scheduler jobs list --location southamerica-east1` |
| Un pedido queda `generando` para siempre | ya no pasa: se rescata solo a los 30 minutos |
| Las piezas salen sin las reglas del club | falta `ASISTIME_CLAVE`. Ver el paso 2 |
