# Prompt para Lovable

Pegá esto en Lovable. Asume que Supabase ya está conectado y que la tabla
`disenos` y el bucket `disenos` ya existen (los crea `supabase.sql`).

---

Necesito una pantalla de chat para pedir diseños de redes sociales del club
Boss Padel. La estética tiene que ser la de la marca: fondo negro `#0A0A0A`,
acento lima `#E4FF02`, texto casi blanco `#FAFAFA`. Tipografías Archivo para
títulos y Barlow para el resto, ambas de Google Fonts. Interfaz en español
rioplatense, con voseo.

## La pantalla

Un chat de una sola columna, centrado, con ancho máximo de 720px.

**Arriba:** el título «Pedidos de diseño» y abajo, más chico y en gris, «Contá
lo que necesitás como se lo dirías a un diseñador».

**En el medio:** el historial de pedidos de la persona, del más viejo al más
nuevo, con scroll automático al final.

**Abajo, fijo:** el compositor.

## El compositor

Un textarea que crece con el contenido, de dos líneas iniciales y máximo ocho.
El placeholder dice: «Una placa para el torneo del Hípico del 12, 13 y 14 de
setiembre, libres de 2da a 6ta y femenina 3ra, 4ta y 5ta».

Arriba del textarea, dos filas de chips seleccionables, chicas y discretas:

- **Formato** (se puede elegir más de uno, arranca con Cuadrado marcado):
  `Cuadrado` · `Story` · `Vertical` · `Tapa de reel` · `Presentación PDF` · `Reel`
- **Sede** (una sola, arranca en Carrasco):
  `Carrasco` · `Hípico` · `Punta del Este` · `Todas`

Los chips seleccionados van con fondo lima y texto negro. Los no seleccionados,
borde gris y texto gris.

A la derecha, un botón redondo de Enviar con una flecha. Se deshabilita si el
textarea está vacío. `Cmd+Enter` también envía.

## Qué pasa al enviar

Insertás en la tabla `disenos` con el cliente de Supabase:

```ts
await supabase.from('disenos').insert({
  user_id: user.id,
  mensaje: texto,
  formatos: formatosElegidos,   // ej: ['post','story']
  sede: sedeElegida,
  quien: perfil?.nombre ?? user.email,
})
```

Los valores de `formatos` tienen que ser exactamente: `post` (Cuadrado),
`story` (Story), `vertical` (Vertical), `reel` (Tapa de reel), `pdf`
(Presentación PDF), `video` (Reel).

Ojo con los dos últimos nombres: `reel` es la **tapa**, una imagen fija para
usar de portada, y `video` es el **reel de verdad**, un mp4. Son piezas
distintas y no comparten valor.

`Presentación PDF` no es un formato más: produce un documento, no una placa.
Cuando está marcado, mostralo con fondo lima igual que los otros, pero si es el
único marcado cambiá el placeholder del textarea por «Una propuesta de
sponsoreo para mandarle a una marca de bebidas, con los números del club y los
planes disponibles». Una presentación tarda más que una placa: entre tres y
cinco minutos.

Limpiás el textarea al instante. No esperes ninguna respuesta del servidor:
la fila aparece sola en el historial por la suscripción.

## Los estados

Cada pedido del historial es una tarjeta que muestra el mensaje que escribió la
persona y, debajo, algo distinto según `estado`:

- **`pendiente`** — «En cola…» con un punto lima que late.
- **`generando`** — «Diseñando…» con una barra de progreso indeterminada y el
  texto en gris «esto tarda unos dos o tres minutos», o «esto tarda unos cinco
  minutos» si el pedido incluye el formato `pdf`.
- **`listo`** — las imágenes de `urls` en una grilla. Cada imagen tiene, al
  pasar el mouse por encima, dos botones sobre la esquina inferior derecha:
  **Ver** (la abre en grande en un modal con fondo negro) y **Descargar**.

  El botón de descargar tiene que bajar el archivo de verdad, no abrirlo en una
  pestaña. Hacé fetch de la URL, convertilo a blob y disparalo con un `<a>` que
  tenga el atributo `download`, con un nombre útil tipo
  `boss-torneo-hipico-post.png`. Si hay más de una imagen, sumá arriba de la
  grilla un botón **Descargar todas**.

  Si el campo `videos` trae algo —un array de `{nombre, url, peso, duracion}`—
  mostralo **arriba de todo lo demás** con un `<video>`: ancho completo,
  relación 9:16, fondo negro, `object-fit: contain`, con `controls`,
  `playsInline` y `preload="metadata"`. **Sin `muted`**: el reel trae efectos
  de sonido y se tienen que poder escuchar. Abajo, la duración en segundos, el
  peso en MB y un botón **Descargar**.

  Si el campo `documentos` trae algo —es un array de `{nombre, url, peso}`—
  mostralo **arriba de las imágenes** como una tarjeta ancha con borde gris,
  un ícono de documento a la izquierda, el nombre del archivo, el peso en MB
  con un decimal, y un botón **Descargar** a la derecha. Es un PDF: no se
  previsualiza, se baja. Usá el mismo truco del blob para que baje de verdad.

  Debajo de las imágenes, el contenido de `copy` en un bloque con fondo gris
  oscuro y un botón «Copiar texto» que lo manda al portapapeles y muestra
  «Copiado» por dos segundos. Si `mensaje_agente` tiene contenido, mostralo en
  un bloque aparte con borde lima a la izquierda y el título «Qué interpretó».
- **`error`** — el texto de `mensaje_agente` en rojo suave, y un botón
  «Reintentar» que vuelve a insertar una fila nueva con el mismo mensaje.

Importante: un pedido puede tardar tres minutos. La persona tiene que poder
seguir escribiendo otros pedidos mientras tanto, sin que la interfaz se bloquee.

## Tiempo real

Suscribite a los cambios de la tabla para que la tarjeta se actualice sola sin
recargar:

```ts
supabase.channel('disenos')
  .on('postgres_changes',
      { event: '*', schema: 'public', table: 'disenos',
        filter: `user_id=eq.${user.id}` },
      recargarOActualizarFila)
  .subscribe()
```

## Autenticación

Login con email y contraseña de Supabase Auth. Si no hay sesión, pantalla de
login simple con la misma estética. Sin registro abierto: las cuentas las crea
el administrador.

## Detalles que importan

- Los `urls` y las `url` de `documentos` son públicos: se muestran y se bajan
  sin autenticación.
- `documentos` puede venir vacío (`[]`). No muestres la tarjeta en ese caso.
- Las imágenes son de 1080×1080 y 1080×1920. Mostralas con `object-fit:
  contain` y fondo negro para que no se deformen.
- En celular todo tiene que funcionar bien: los chips en dos filas con scroll
  horizontal, y las imágenes a ancho completo.
- No inventes pantallas de administración ni de configuración. Solo el chat.
