// Publicar en Instagram, desde el chat de Asistime.
//
// Tres puertas, y la diferencia entre ellas es lo único que hay que entender:
//
//   POST /api-publicar        una PIEZA que el sistema diseñó. Se nombra por su
//                             `diseno_id` y nunca por una URL.
//   POST /api-publicar/foto   un ARCHIVO tal cual, sin diseñar: una foto O un
//                             video que la persona adjuntó en el chat. Sirve
//                             para lo que ya está listo — la foto de la
//                             fachada, el video que grabó alguien del club.
//                             Se llama `/foto` por historia: cuando se
//                             escribió sólo aceptaba imágenes.
//   POST /api-publicar/reel   un VIDEO hecho por el motor de reels. Se nombra
//                             por su `reel_id` y el archivo ya es nuestro.
//
// Las dos últimas terminan en el mismo lugar que la primera: anotan un diseño
// y siguen por el camino de siempre. Ver la nota de abajo.
//
// ── La regla que esta función no rompe ────────────────────────────────────
//
// «Nada se publica solo»: una fila en `publicaciones` la crea una persona. El
// worker no decide publicar por su cuenta y el agente de diseño no escribe en
// esa tabla — el día que se equivoque en una placa, que el error quede en una
// pantalla y no en el feed del cliente.
//
// Acá del otro lado del chat hay una persona, así que la regla se mantiene:
// quien pide publicar es ella. Lo que esta función agrega son los tres cierres
// que un chat necesita y un botón no:
//
//   1. **Sólo publica lo que pasó por acá.** Nada se publica desde la URL que
//      le dicten: el archivo se BAJA, se verifica POR SUS BYTES que sea una
//      imagen o un video de verdad, y se guarda en el Storage del cliente. A
//      las fotos además se les sacan los metadatos. Lo que sale a Instagram es
//      siempre nuestra copia. Una URL que no se pueda bajar, o que no sea ni
//      imagen ni video, no llega a la cola.
//   2. **Un diseño no se publica dos veces.** Si ya hay una publicación en
//      curso o publicada, contesta 409 con los datos de esa. Sin esto, que el
//      modelo llame dos veces —que llama— duplica el posteo.
//   3. **Falla temprano y en voz alta.** Si no hay cuenta de Instagram, o el
//      diseño no está listo, o la pieza no entra en el feed, lo dice ahora y
//      no dentro de veinte minutos en una fila que nadie mira.
//
// ── Por qué una foto suelta —o un reel— también crea una fila en `disenos` ─
//
// Porque después de esa fila TODO el camino ya está escrito y probado: el
// freno de publicar dos veces, la medición de la pieza, la elección entre
// feed y story, la consulta de estado y el worker que sube. Una foto
// publicada directo no es un caso aparte: es un diseño de una sola imagen que
// nadie dibujó.
//
// Además deja registro. Sin la fila, lo que sale al Instagram de la clínica
// por esta puerta no quedaría anotado en ningún lado.
//
// Con el reel es igual, con una diferencia: el video NO se copia, porque ya
// está en nuestro bucket —lo subió el motor de reels—. Bajarlo y volverlo a
// subir sería mover diez megas para dejarlos donde ya estaban.
//
// Publicar en sí sigue siendo del worker: esta función sólo escribe la fila.
// Es una cola porque publicar tarda y puede fallar a la mitad.

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-api-clave",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
};

// Tope por hora. Instagram permite 100 posteos diarios; esto no está para
// cuidar ese límite sino para que un bucle en el chat no vacíe el calendario
// de contenido del cliente en diez minutos.
const MAX_POR_HORA = 10;

// Lo que el feed acepta: de 4:5 a 1.91:1. Una story de 1080×1920 da 0,5625 y
// no entra — no es una decisión de diseño, no entra. Se chequea acá para poder
// decir QUÉ pieza está mal, en vez de recibir de Meta un «media no soportada».
const FEED_MIN = 0.795, FEED_MAX = 1.915;

const VIDEO = /\.(mp4|mov)$/i;

// Lo que se acepta cuando lo que se publica es una foto tal cual. Mismos
// números que en `api-disenos`: una foto de celular pesa entre 2 y 5 MB.
const MAX_BYTES = 12 * 1024 * 1024;

// Y lo que se acepta cuando es un VIDEO. Instagram aguanta mucho más, pero
// esta función tiene que pasarlo por su propia memoria: 80 MB entran cómodos y
// cubren de sobra un video de celular de un minuto. Más que eso conviene que
// alguien lo suba a mano antes que arriesgar que se corte a la mitad.
const MAX_VIDEO_BYTES = 80 * 1024 * 1024;

const TIPOS_VIDEO: Record<string, string> = {
  mp4: "video/mp4", mov: "video/quicktime",
};

const TIPOS: Record<string, string> = {
  jpg: "image/jpeg", png: "image/png",
  webp: "image/webp", gif: "image/gif",
};

const TD = new TextDecoder();

// Cuánto espera el GET a que la publicación salga antes de contestar «todavía
// no». El worker corre cada minuto, así que esperando algo más de eso la
// mayoría de las consultas contestan con el link ya puesto.
//
// La espera vive ACÁ y no en la tool de Asistime porque el sandbox de las
// tools no sabe dormir: un `setTimeout` no lo suspende, lo mata. Ver la nota
// larga en `api-disenos`.
const ESPERA_MAX_MS = 75_000;
const ESPERA_PASO_MS = 5_000;

const dormir = (ms: number) => new Promise((r) => setTimeout(r, ms));

function json(cuerpo: unknown, status = 200) {
  return new Response(JSON.stringify(cuerpo), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

/** Ancho y alto de una imagen, sin bajar el archivo entero.
 *
 * Se mide en vez de adivinar por el nombre porque el nombre lo escribe el
 * agente y puede decir cualquier cosa; los píxeles no mienten. Y de esta
 * medida depende algo que se ve: si la pieza va al feed o va a stories.
 *
 * En PNG las medidas están en los primeros 24 bytes. En JPEG están en el
 * marcador SOF, que puede caer bastante más adentro — por eso se piden 128 KB
 * y no 34. Antes sólo se leía PNG, y con una foto de celular —que es JPEG— la
 * medición fallaba en silencio y se caía a adivinar por el nombre del
 * archivo: toda foto vertical terminaba clasificada como cuadrada. */
function medirPng(b: Uint8Array): [number, number] | null {
  if (b.length < 24 || b[0] !== 0x89 || b[1] !== 0x50) return null;
  const dv = new DataView(b.buffer, b.byteOffset, b.byteLength);
  return [dv.getUint32(16), dv.getUint32(20)];
}

function medirJpg(b: Uint8Array): [number, number] | null {
  if (b.length < 4 || b[0] !== 0xFF || b[1] !== 0xD8) return null;
  let i = 2;
  while (i + 9 < b.length) {
    if (b[i] !== 0xFF) { i++; continue; }
    const m = b[i + 1];
    // Los SOF —donde viven las medidas— son C0..CF menos C4, C8 y CC, que son
    // tablas y no encabezados de cuadro.
    if (m >= 0xC0 && m <= 0xCF && m !== 0xC4 && m !== 0xC8 && m !== 0xCC) {
      return [(b[i + 7] << 8) | b[i + 8], (b[i + 5] << 8) | b[i + 6]];
    }
    if (m === 0xD8 || m === 0x01 || (m >= 0xD0 && m <= 0xD7)) { i += 2; continue; }
    const largo = (b[i + 2] << 8) | b[i + 3];
    if (largo < 2) return null;
    i += 2 + largo;
  }
  return null;
}

async function medir(url: string): Promise<[number, number] | null> {
  try {
    const r = await fetch(url, { headers: { Range: "bytes=0-131071" } });
    if (!r.ok) return null;
    const b = new Uint8Array(await r.arrayBuffer());
    return medirPng(b) || medirJpg(b);
  } catch {
    return null;
  }
}

/** Corta el texto donde arrancan las notas internas del diseñador.
 *
 * Es la última defensa y se aplica SIEMPRE, incluso cuando el caption viene
 * dado por quien llama. El 9/8/2026 un agente mandó el `copy.txt` entero como
 * caption y el bloque «QUÉ INTERPRETÉ» —ocho notas de trabajo— terminó público
 * en la cuenta del club. Confiar en que el de arriba mandó sólo el copy no
 * alcanza: si el texto trae las notas, se cortan acá y listo. */
function limpiar_caption(txt: string): string {
  const lineas = (txt || "").split("\n");
  const corte = lineas.findIndex((l) => {
    const t = l.trim().toUpperCase();
    // La tilde de «QUÉ» a veces no está, y el separador de tres guiones sólo
    // aparece cuando abajo viene material que no es del posteo.
    return t.startsWith("QUÉ INTERPRET") || t.startsWith("QUE INTERPRET") ||
      /^-{3,}$/.test(l.trim());
  });
  return (corte >= 0 ? lineas.slice(0, corte) : lineas).join("\n").trim();
}

/** El caption que va a Instagram, sacado del `copy` del diseño.
 *
 * `copy.txt` trae varias secciones —el texto del posteo y después «QUÉ
 * INTERPRETÉ», que es una nota para quien pidió la pieza—. Publicar el archivo
 * entero sería publicar las notas internas del diseñador. */
function caption_de(copy: string): string {
  const lineas = (copy || "").split("\n");
  const secciones: { titulo: string; cuerpo: string[] }[] = [];
  let actual: { titulo: string; cuerpo: string[] } | null = null;
  for (let i = 0; i < lineas.length; i++) {
    const que_sigue = lineas[i + 1] || "";
    if (lineas[i].trim() && /^-{3,}$/.test(que_sigue.trim())) {
      actual = { titulo: lineas[i].trim().toUpperCase(), cuerpo: [] };
      secciones.push(actual);
      i++;
      continue;
    }
    if (actual) actual.cuerpo.push(lineas[i]);
  }
  // Si hay una sección que se llama COPY, esa es. Si no hay ninguna, el copy
  // arranca arriba de todo: se toma lo que está antes de las notas. Antes acá
  // se caía a `secciones[0]`, que cuando la única sección era «QUÉ INTERPRETÉ»
  // devolvía justo lo que no había que publicar.
  const conCopy = secciones.find((s) => s.titulo.includes("COPY"));
  return limpiar_caption(conCopy ? conCopy.cuerpo.join("\n") : copy);
}

// ── Traer la foto que mandó la persona ───────────────────────────────────
//
// Todo esto es COPIA LITERAL de `api-disenos`, igual que en `api-plantillas` y
// por lo mismo: es el mismo problema y ya está resuelto ahí. Escribir una
// tercera versión sería garantizar que dentro de seis meses alguien arregle
// una y no las otras.
//
// La URL que da el chat es de otra plataforma y puede estar firmada por unos
// minutos. Además es una URL que alguien DICTÓ, y publicar lo que a uno le
// dictan es exactamente lo que esta función no hace: se baja, se verifica que
// sea una imagen por sus bytes, se le sacan los metadatos y se guarda en el
// Storage del cliente. Lo que sale a Instagram es nuestra copia.

function unir(partes: Uint8Array[]): Uint8Array {
  let n = 0;
  for (const p of partes) n += p.length;
  const salida = new Uint8Array(n);
  let i = 0;
  for (const p of partes) { salida.set(p, i); i += p.length; }
  return salida;
}

/** Qué es el archivo, por sus primeros bytes y no por la extensión de la URL:
 *  muchas URLs de chat no tienen extensión, y la que tienen puede mentir. */
function formato(b: Uint8Array): string | null {
  if (b.length < 12) return null;
  if (b[0] === 0xFF && b[1] === 0xD8 && b[2] === 0xFF) return "jpg";
  if (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4E && b[3] === 0x47) return "png";
  if (b[0] === 0x52 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x46 &&
      b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50) return "webp";
  if (b[0] === 0x47 && b[1] === 0x49 && b[2] === 0x46) return "gif";
  return null;
}

/** ¿Es un video? MP4 y MOV se reconocen por la caja `ftyp`, que está en los
 *  bytes 4 a 8. Se mira igual que las imágenes —por los bytes y no por la
 *  extensión— porque la URL de un chat muchas veces no tiene ninguna. */
function formatoVideo(b: Uint8Array): string | null {
  if (b.length < 12) return null;
  if (TD.decode(b.subarray(4, 8)) !== "ftyp") return null;
  // `qt  ` es QuickTime, o sea .mov. El resto de las marcas conocidas
  // —isom, mp42, avc1, iso5— son MP4.
  return TD.decode(b.subarray(8, 12)) === "qt  " ? "mov" : "mp4";
}

/** Los primeros bytes de una URL, y cuánto pesa el archivo entero.
 *
 *  Existe para no bajar cincuenta megas y descubrir después que no servían.
 *  Doce bytes alcanzan para saber si es foto o video, y el `content-range` de
 *  la misma respuesta trae el tamaño total.
 *
 *  Si el servidor ignora el `Range` y manda todo, se lee el primer pedazo y se
 *  corta la conexión. Muchos servidores de chat hacen exactamente eso.
 */
async function asomarse(url: string, n: number):
    Promise<{ cabeza: Uint8Array; total: number }> {
  const r = await fetch(url, {
    headers: { Range: `bytes=0-${n - 1}` },
    signal: AbortSignal.timeout(20000),
  });
  if (!r.ok) throw new Error(`el servidor contestó ${r.status}`);

  // `bytes 0-65535/12345678` → 12345678. Si no vino el rango, el
  // `content-length` sirve sólo cuando la respuesta ES el archivo entero.
  const rango = r.headers.get("content-range") || "";
  const total = Number(rango.split("/")[1] ||
                       (r.status === 200 ? r.headers.get("content-length") : 0) || 0);

  const lector = r.body!.getReader();
  const trozos: Uint8Array[] = [];
  let leidos = 0;
  while (leidos < n) {
    const { done, value } = await lector.read();
    if (done) break;
    trozos.push(value);
    leidos += value.length;
  }
  await lector.cancel().catch(() => {});
  return { cabeza: unir(trozos), total };
}

function limpiarJpg(b: Uint8Array): Uint8Array | null {
  const partes = [b.subarray(0, 2)];
  let i = 2;
  while (true) {
    if (i + 4 > b.length || b[i] !== 0xFF) return null;
    const m = b[i + 1];
    // 0xDA es el comienzo de la imagen comprimida: de ahí al final va tal cual.
    if (m === 0xDA) { partes.push(b.subarray(i)); break; }
    const largo = (b[i + 2] << 8) | b[i + 3];
    if (largo < 2 || i + 2 + largo > b.length) return null;
    // APP1..APP15 es donde viven EXIF, GPS y XMP. COM es el comentario.
    // APP0 (JFIF) se conserva: describe la imagen, no a quien la sacó.
    const meta = (m >= 0xE1 && m <= 0xEF) || m === 0xFE;
    if (!meta) partes.push(b.subarray(i, i + 2 + largo));
    i += 2 + largo;
  }
  return unir(partes);
}

function limpiarPng(b: Uint8Array): Uint8Array | null {
  const fuera = new Set(["tEXt", "zTXt", "iTXt", "eXIf", "tIME"]);
  const partes = [b.subarray(0, 8)];
  let i = 8;
  while (i + 12 <= b.length) {
    const dv = new DataView(b.buffer, b.byteOffset + i, 8);
    const largo = dv.getUint32(0);
    const tipo = TD.decode(b.subarray(i + 4, i + 8));
    const fin = i + 12 + largo;
    if (fin > b.length) return null;
    if (!fuera.has(tipo)) partes.push(b.subarray(i, fin));
    i = fin;
    if (tipo === "IEND") break;
  }
  return unir(partes);
}

function limpiarWebp(b: Uint8Array): Uint8Array | null {
  const partes = [b.subarray(0, 12)];
  let flags = -1;
  let escritos = 12;
  let i = 12;
  while (i + 8 <= b.length) {
    const dv = new DataView(b.buffer, b.byteOffset + i, 8);
    const tipo = TD.decode(b.subarray(i, i + 4));
    const largo = dv.getUint32(4, true);
    const fin = i + 8 + largo + (largo % 2);
    if (fin > b.length) return null;
    if (tipo !== "EXIF" && tipo !== "XMP ") {
      if (tipo === "VP8X") flags = escritos + 8;
      partes.push(b.subarray(i, fin));
      escritos += fin - i;
    }
    i = fin;
  }
  const salida = unir(partes);
  // Bajar las banderas de EXIF y XMP del chunk VP8X: sacar los chunks sin
  // bajarlas deja un archivo que dice tener metadatos que ya no están, y los
  // decodificadores estrictos rechazan la imagen entera. Ver la nota larga en
  // `api-disenos`.
  if (flags >= 0 && flags < salida.length) salida[flags] &= ~(0x08 | 0x04);
  new DataView(salida.buffer).setUint32(4, salida.length - 8, true);
  return salida;
}

/** Saca todo lo que la foto cuenta sobre quién la sacó y dónde.
 *
 * Acá pesa más que en `api-disenos`: allá la foto termina redibujada por
 * Chromium y los metadatos se pierden solos, pero lo que se publica por esta
 * puerta es el archivo tal cual. Si trae las coordenadas de dónde se tomó,
 * salen a Instagram.
 *
 * No re-comprime: mueve bytes, no píxeles. */
function limpiar(b: Uint8Array, fmt: string): Uint8Array {
  try {
    const r = fmt === "jpg" ? limpiarJpg(b)
            : fmt === "png" ? limpiarPng(b)
            : fmt === "webp" ? limpiarWebp(b) : null;
    return r || b;
  } catch {
    return b;
  }
}

/** ¿Es una URL que tiene sentido ir a buscar? Nadie de afuera llega acá sin
 *  la clave, pero una función que baja cualquier dirección que le dicten es
 *  una función que puede ser usada para mirar adentro de la red. */
function direccion_valida(u: string): boolean {
  let url: URL;
  try { url = new URL(u); } catch { return false; }
  if (url.protocol !== "https:" && url.protocol !== "http:") return false;
  const h = url.hostname.toLowerCase();
  if (h === "localhost" || h.endsWith(".localhost") || h === "::1") return false;
  if (/^127\./.test(h) || /^10\./.test(h) || /^192\.168\./.test(h)) return false;
  if (/^169\.254\./.test(h)) return false;
  if (/^172\.(1[6-9]|2\d|3[01])\./.test(h)) return false;
  return true;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

  const esperada = Deno.env.get("API_CLAVE");
  if (!esperada) return json({ error: "falta configurar API_CLAVE" }, 500);
  const dada = req.headers.get("x-api-clave") || "";
  if (dada.length !== esperada.length) return json({ error: "clave inválida" }, 401);
  let iguales = 0;
  for (let i = 0; i < esperada.length; i++) {
    iguales |= dada.charCodeAt(i) ^ esperada.charCodeAt(i);
  }
  if (iguales !== 0) return json({ error: "clave inválida" }, 401);

  const base = Deno.env.get("SUPABASE_URL")!;
  const llave = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const usuario = Deno.env.get("USUARIO_ID") || null;
  const cab = {
    apikey: llave,
    Authorization: `Bearer ${llave}`,
    "Content-Type": "application/json",
  };

  const traer_publicaciones = async (diseno: string) => {
    const r = await fetch(
      `${base}/rest/v1/publicaciones?diseno_id=eq.${encodeURIComponent(diseno)}` +
      `&select=id,tipo,estado,permalink,mensaje,publicar_en,urls` +
      `&order=creado_en.asc`,
      { headers: cab },
    );
    return r.ok ? await r.json() : [];
  };

  const ruta = new URL(req.url).pathname;
  const esFoto = ruta.endsWith("/foto");
  const esReel = ruta.endsWith("/reel");

  // ── Cómo va la publicación ──────────────────────────────────────────────
  if (req.method === "GET") {
    const url0 = new URL(req.url);
    const diseno = url0.searchParams.get("diseno_id");
    if (!diseno) return json({ error: "falta el parámetro diseno_id" }, 400);
    const esperar = url0.searchParams.get("esperar") !== "no";

    const hasta = Date.now() + (esperar ? ESPERA_MAX_MS : 0);
    for (;;) {
      const filas = await traer_publicaciones(diseno);

      // Sin ninguna fila no hay nada que esperar: a este diseño nadie lo mandó
      // a publicar. Esperar acá sería tener al chat mudo setenta y cinco
      // segundos por una respuesta que ya se sabe.
      if (!filas.length) {
        return json({
          diseno_id: diseno,
          publicaciones: [],
          terminado: true,
          mensaje: "Este diseño todavía no se mandó a publicar.",
        });
      }

      const activas = filas.filter((f: any) =>
        f.estado === "programado" || f.estado === "subiendo");

      // Una publicación programada para dentro de tres horas no es una
      // demora: es lo que se pidió. Contestar ya, en vez de esperar por algo
      // que no va a pasar en este minuto.
      const inminente = activas.some((f: any) =>
        !f.publicar_en ||
        new Date(f.publicar_en).getTime() <= Date.now() + 120_000);

      const cuerpo = {
        diseno_id: diseno,
        terminado: activas.length === 0,
        publicaciones: filas.map((f: any) => ({
          id: f.id,
          tipo: f.tipo,
          estado: f.estado,
          cuando: f.publicar_en,
          permalink: f.permalink || null,
          mensaje: f.mensaje || null,
        })),
      };

      if (cuerpo.terminado || !inminente || Date.now() >= hasta) {
        return json(cuerpo);
      }
      await dormir(ESPERA_PASO_MS);
    }
  }

  if (req.method !== "POST") return json({ error: "usá POST o GET" }, 405);

  let cuerpo: any;
  try {
    cuerpo = await req.json();
  } catch {
    return json({ error: "el cuerpo tiene que ser JSON" }, 400);
  }

  let diseno_id = String(cuerpo.diseno_id || "").trim();
  if (!diseno_id && !esFoto && !esReel) {
    return json({ error: "falta diseno_id" }, 400);
  }

  // ── ¿Hay cuenta de Instagram? ───────────────────────────────────────────
  // Primero de todo: sin cuenta conectada, la fila quedaría esperando para
  // siempre y el chat diría «ya sale».
  const ri = await fetch(
    `${base}/rest/v1/instagram_estado?select=usuario,activa,mensaje&limit=1`,
    { headers: cab });
  if (!ri.ok) {
    return json({
      error: "Esta marca todavía no tiene Instagram conectado, así que no " +
             "puedo publicar. Se conecta desde la app.",
      codigo: "sin_instagram",
    }, 409);
  }
  const [cuenta] = await ri.json();
  if (!cuenta || cuenta.activa !== true) {
    return json({
      error: cuenta?.mensaje ||
             "La cuenta de Instagram no está activa. Hay que reconectarla " +
             "desde la app antes de publicar.",
      codigo: "sin_instagram",
    }, 409);
  }

  // ── Una foto tal cual: se copia y se anota como un diseño de una imagen ──
  //
  // Después de esto, `diseno_id` apunta a una fila normal de `disenos` y todo
  // lo que sigue —el freno de publicar dos veces, la medición, la elección
  // entre feed y story, la consulta de estado, el worker— funciona sin saber
  // que esta pieza no la dibujó nadie.
  if (esFoto) {
    // `foto` es el nombre viejo y sigue andando; `archivo` es el que
    // corresponde ahora que por acá también entra un video.
    const origen = String(cuerpo.archivo ?? cuerpo.foto ?? cuerpo.video ?? "").trim();
    if (!origen) {
      return json({ error: "falta el archivo: una URL https que se pueda bajar",
                    codigo: "falta_la_foto" }, 400);
    }
    if (!direccion_valida(origen)) {
      return json({
        error: "Tiene que ser una URL pública que se pueda descargar.",
        codigo: "foto_invalida",
      }, 400);
    }

    // Primero se ASOMA: doce bytes dicen si es foto o video, y traer un video
    // de cincuenta megas a la memoria para descubrir que no servía sería
    // pagar el viaje entero por una pregunta de doce bytes.
    let cabeza: Uint8Array, pesa: number;
    try {
      ({ cabeza, total: pesa } = await asomarse(origen, 65536));
    } catch (e) {
      return json({
        error: `No pude bajar el archivo: ${(e as Error).message}. Pedile a ` +
               `la persona que lo mande de nuevo.`,
        codigo: "foto_no_sirve",
      }, 400);
    }

    const fmt = formato(cabeza);
    const vid = fmt ? null : formatoVideo(cabeza);

    if (!fmt && !vid) {
      return json({
        error: "Eso no es ni una imagen ni un video de los que Instagram " +
               "acepta. Las fotos van en JPG o PNG y los videos en MP4 o MOV.",
        codigo: "foto_no_sirve",
      }, 400);
    }

    // ── Si es un VIDEO ──────────────────────────────────────────────────
    //
    // No se re-empaqueta ni se le sacan metadatos: se copia tal cual. Un
    // video no lleva las coordenadas del celular como una foto, y volver a
    // codificarlo acá sería tardar minutos para empeorar la imagen.
    //
    // Se copia igual, en vez de publicar la URL que dictaron, por la misma
    // razón que la foto: la del chat se vence en un rato, e Instagram tarda
    // en procesar un video. Si la URL muere en el medio, el posteo falla sin
    // que nadie entienda por qué.
    if (vid) {
      if (pesa > MAX_VIDEO_BYTES) {
        return json({
          error: `El video pesa ${Math.round(pesa / 1048576)} MB y el tope ` +
                 `son 80. Habría que subirlo a mano, o mandar uno más corto.`,
          codigo: "video_muy_pesado",
        }, 400);
      }

      const rutaVid = `publicaciones/${crypto.randomUUID()}.${vid}`;
      let rv: Response;
      try {
        rv = await fetch(origen, { signal: AbortSignal.timeout(120000) });
        if (!rv.ok) throw new Error(`el servidor contestó ${rv.status}`);
      } catch (e) {
        return json({
          error: `No pude bajar el video: ${(e as Error).message}.`,
          codigo: "foto_no_sirve",
        }, 400);
      }

      // El cuerpo va como flujo y no como bloque: así el video pasa de una
      // punta a la otra sin quedar entero en la memoria de esta función.
      const upv = await fetch(`${base}/storage/v1/object/disenos/${rutaVid}`, {
        method: "POST",
        headers: {
          apikey: llave,
          Authorization: `Bearer ${llave}`,
          "Content-Type": TIPOS_VIDEO[vid],
        },
        body: rv.body,
      });
      if (!upv.ok) {
        console.error("storage video", upv.status, (await upv.text()).slice(0, 300));
        return json({ error: "no pude guardar el video" }, 500);
      }
      const nuestroVid =
        `${base}/storage/v1/object/public/disenos/${rutaVid}`;

      const filaV: Record<string, unknown> = {
        mensaje: "Video publicado tal cual desde el chat, sin diseñar.",
        formatos: ["reel"],
        estado: "listo",
        titulo: String(cuerpo.titulo || "Video sin diseñar").slice(0, 200),
        quien: String(cuerpo.quien || "Asistime").slice(0, 120),
        urls: [],
        videos: [{ url: nuestroVid }],
      };
      if (usuario) filaV.user_id = usuario;
      if (typeof cuerpo.caption === "string" && cuerpo.caption.trim()) {
        filaV.copy = String(cuerpo.caption).slice(0, 2200);
      }

      const rnv = await fetch(`${base}/rest/v1/disenos`, {
        method: "POST",
        headers: { ...cab, Prefer: "return=representation" },
        body: JSON.stringify(filaV),
      });
      if (!rnv.ok) {
        console.error("insert video", rnv.status, (await rnv.text()).slice(0, 300));
        return json({ error: "no pude registrar el video" }, 500);
      }
      const [creadoV] = await rnv.json();
      diseno_id = creadoV.id;
    }

    // ── Si es una FOTO ──────────────────────────────────────────────────
    if (fmt) {
      let crudo: Uint8Array;
      try {
        const rf = await fetch(origen, { signal: AbortSignal.timeout(20000) });
        if (!rf.ok) throw new Error(`el servidor contestó ${rf.status}`);
        crudo = new Uint8Array(await rf.arrayBuffer());
      } catch (e) {
        return json({
          error: `No pude bajar la foto: ${(e as Error).message}. Pedile a la ` +
                 `persona que la mande de nuevo.`,
          codigo: "foto_no_sirve",
        }, 400);
      }
      if (crudo.length > MAX_BYTES) {
        return json({ error: "La foto pesa más de 12 MB.",
                      codigo: "foto_no_sirve" }, 400);
      }
      // GIF no: Instagram no lo publica como imagen y lo que sale es un cuadro
      // quieto. Mejor decirlo que publicar algo que no es lo que esperan.
      if (fmt === "gif") {
        return json({
          error: "Instagram no publica GIFs como foto: sale un cuadro quieto. " +
                 "Si es una animación tiene que ir como video.",
          codigo: "foto_no_sirve",
        }, 400);
      }

      const rutaFoto = `publicaciones/${crypto.randomUUID()}.${fmt}`;
      const up = await fetch(`${base}/storage/v1/object/disenos/${rutaFoto}`, {
        method: "POST",
        headers: {
          apikey: llave,
          Authorization: `Bearer ${llave}`,
          "Content-Type": TIPOS[fmt],
        },
        body: limpiar(crudo, fmt),
      });
      if (!up.ok) {
        console.error("storage", up.status, (await up.text()).slice(0, 300));
        return json({ error: "no pude guardar la foto" }, 500);
      }
      const nuestra = `${base}/storage/v1/object/public/disenos/${rutaFoto}`;

      const fila: Record<string, unknown> = {
        mensaje: "Foto publicada tal cual desde el chat, sin diseñar.",
        formatos: ["post"],
        estado: "listo",
        titulo: String(cuerpo.titulo || "Foto sin diseñar").slice(0, 200),
        quien: String(cuerpo.quien || "Asistime").slice(0, 120),
        urls: [nuestra],
      };
      if (usuario) fila.user_id = usuario;
      if (typeof cuerpo.caption === "string" && cuerpo.caption.trim()) {
        fila.copy = String(cuerpo.caption).slice(0, 2200);
      }

      const rn = await fetch(`${base}/rest/v1/disenos`, {
        method: "POST",
        headers: { ...cab, Prefer: "return=representation" },
        body: JSON.stringify(fila),
      });
      if (!rn.ok) {
        console.error("insert diseno", rn.status, (await rn.text()).slice(0, 300));
        return json({ error: "no pude registrar la foto" }, 500);
      }
      const [creado] = await rn.json();
      diseno_id = creado.id;
    }
  }

  // ── Un reel: se enchufa al camino que ya existe ─────────────────────────
  //
  // Mismo truco que la foto y por la misma razón: se anota como un diseño de
  // un solo video. De ahí para abajo, el freno de publicar dos veces, la
  // elección entre feed y story, la consulta de estado y el worker funcionan
  // sin saber que esta pieza salió de otra tabla.
  //
  // La diferencia con la foto es que el video NO se copia: ya vive en nuestro
  // bucket —lo subió el propio motor de reels— así que bajarlo y volverlo a
  // subir sería mover 10 MB para dejarlos en el mismo lugar.
  if (esReel) {
    const reel_id = String(cuerpo.reel_id || "").trim();
    if (!reel_id) {
      return json({ error: "falta reel_id: el id que devolvió crear_reel",
                    codigo: "falta_el_reel" }, 400);
    }

    // El id es un UUID, y se chequea ANTES de preguntarle a la base. El
    // 28/8/2026, el primer día que esto existió, el agente mandó el NOMBRE DEL
    // ARCHIVO («Prop_plane_flying_with_banner_...mp4»). PostgREST contestó 400
    // porque eso no es un uuid, y de acá salía «esta marca no hace reels»: una
    // respuesta FALSA —los hace— que manda a mirar al lugar equivocado. Un id
    // con forma rara es un error de quien llama y hay que decírselo así.
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
          .test(reel_id)) {
      return json({
        error: `«${reel_id}» no es el id de un reel: el id es un uuid y lo ` +
               `devuelve crear_reel. No es el nombre del archivo ni el final ` +
               `de la URL del video.`,
        codigo: "reel_id_invalido",
      }, 400);
    }

    const rr = await fetch(
      `${base}/rest/v1/reels?id=eq.${encodeURIComponent(reel_id)}` +
      `&select=id,estado,url,titulo,notas&limit=1`,
      { headers: cab });
    if (!rr.ok) {
      // Acá ya no se puede decir «esta marca no hace reels»: con un id bien
      // formado, que la consulta falle es un problema nuestro, no del pedido.
      // Si la tabla no existiera —una marca sin video— también cae acá, así
      // que el mensaje tiene que servir para los dos casos sin mentir en
      // ninguno.
      console.error("leer reel", rr.status, (await rr.text()).slice(0, 300));
      return json({
        error: "No pude buscar ese reel. Puede que esta marca todavía no " +
               "tenga el motor de video prendido; si lo tiene, es un " +
               "problema nuestro y hay que avisar al equipo.",
        codigo: "no_pude_leer_el_reel",
      }, 502);
    }
    const [reel] = await rr.json();
    if (!reel) {
      return json({ error: "No existe ningún reel con ese id.",
                    codigo: "no_existe" }, 404);
    }
    if (reel.estado !== "listo" || !reel.url) {
      return json({
        error: reel.estado === "error" || reel.estado === "rechazado"
          ? `Ese reel no llegó a hacerse (${reel.estado}). ` + (reel.notas || "")
          : "El video todavía no está listo. Esperá a que termine antes de " +
            "publicarlo.",
        codigo: "no_esta_listo",
        estado: reel.estado,
      }, 409);
    }

    // Si este reel ya se anotó antes, se REUSA ese diseño en vez de crear uno
    // nuevo. No es una optimización: es lo que hace que el freno de «ya se
    // publicó» —que mira por diseño— también valga para los reels. Sin esto,
    // dos llamadas seguidas serían dos diseños distintos y dos posteos.
    const marca_id = `[reel ${reel_id}]`;
    const rv = await fetch(
      `${base}/rest/v1/disenos?mensaje=like.*${encodeURIComponent(marca_id)}*` +
      `&select=id&limit=1`,
      { headers: cab });
    const [ya] = rv.ok ? await rv.json() : [];

    if (ya) {
      diseno_id = ya.id;
    } else {
      const filaR: Record<string, unknown> = {
        mensaje: `Reel publicado desde el chat, sin diseñar. ${marca_id}`,
        formatos: ["reel"],
        estado: "listo",
        titulo: String(reel.titulo || cuerpo.titulo || "Reel").slice(0, 200),
        quien: String(cuerpo.quien || "Asistime").slice(0, 120),
        urls: [],
        videos: [{ url: reel.url }],
      };
      if (usuario) filaR.user_id = usuario;
      if (typeof cuerpo.caption === "string" && cuerpo.caption.trim()) {
        filaR.copy = String(cuerpo.caption).slice(0, 2200);
      }
      const rn2 = await fetch(`${base}/rest/v1/disenos`, {
        method: "POST",
        headers: { ...cab, Prefer: "return=representation" },
        body: JSON.stringify(filaR),
      });
      if (!rn2.ok) {
        console.error("insert reel", rn2.status, (await rn2.text()).slice(0, 300));
        return json({ error: "no pude registrar el reel" }, 500);
      }
      const [creadoR] = await rn2.json();
      diseno_id = creadoR.id;
    }
  }

  // ── El diseño ───────────────────────────────────────────────────────────
  const rd = await fetch(
    `${base}/rest/v1/disenos?id=eq.${encodeURIComponent(diseno_id)}` +
    `&select=id,estado,titulo,urls,videos,copy&limit=1`,
    { headers: cab });
  if (!rd.ok) return json({ error: "no pude leer el diseño" }, 502);
  const [d] = await rd.json();
  if (!d) return json({ error: "No existe ningún diseño con ese id." }, 404);
  if (d.estado !== "listo") {
    return json({
      error: "El diseño todavía no está listo. Esperá a que termine antes " +
             "de publicarlo.",
      codigo: "no_esta_listo",
      estado: d.estado,
    }, 409);
  }

  // ── ¿Ya se publicó? ─────────────────────────────────────────────────────
  // El cierre que más importa. Un modelo que no ve una respuesta clara vuelve
  // a llamar, y publicar dos veces lo mismo en la cuenta del cliente no se
  // deshace desde acá.
  const previas = (await traer_publicaciones(diseno_id))
    .filter((f: any) => ["programado", "subiendo", "publicado"].includes(f.estado));
  if (previas.length && !cuerpo.forzar) {
    return json({
      error: "Este diseño ya se mandó a publicar. No lo mando de nuevo para " +
             "no duplicar el posteo.",
      codigo: "ya_publicado",
      publicaciones: previas.map((f: any) => ({
        id: f.id, tipo: f.tipo, estado: f.estado, permalink: f.permalink || null,
      })),
    }, 409);
  }

  // ── Qué piezas hay, y de qué tipo ───────────────────────────────────────
  const videos = ((d.videos || []) as any[])
    .map((v) => v?.url).filter((u: string) => u && VIDEO.test(u));
  const imagenes: { url: string; ratio: number; medida: boolean }[] = [];
  for (const u of (d.urls || []) as string[]) {
    if (!u || VIDEO.test(u)) continue;
    const m = await medir(u);
    imagenes.push(m
      ? { url: u, ratio: m[0] / m[1], medida: true }
      // Si no se pudo medir, el nombre es lo único que queda. Se marca como
      // no medida para poder decirlo en la respuesta en vez de fingir certeza.
      : { url: u, ratio: /story|vert/i.test(u) ? 0.5625 : 1, medida: false });
  }

  const feed = imagenes.filter((i) => i.ratio >= FEED_MIN && i.ratio <= FEED_MAX);
  const verticales = imagenes.filter((i) => i.ratio < FEED_MIN);

  const opciones: { tipo: string; urls: string[]; piezas: number }[] = [];
  if (videos.length) {
    opciones.push({ tipo: "reel", urls: [videos[0]], piezas: 1 });
  }
  if (feed.length === 1) {
    opciones.push({ tipo: "post", urls: [feed[0].url], piezas: 1 });
  } else if (feed.length > 1) {
    // Un carrusel de 10 es UN solo posteo contra el límite diario: es por
    // lejos la forma más barata de publicar varias piezas.
    opciones.push({
      tipo: "carrusel",
      urls: feed.slice(0, 10).map((i) => i.url),
      piezas: Math.min(feed.length, 10),
    });
  }
  // Una story puede ser una imagen vertical O un video: Instagram acepta las
  // dos y el worker ya sabe armar las dos. Faltaba decirlo acá, y por eso un
  // video sólo se podía publicar como reel.
  //
  // Cuando hay video manda el video: si alguien generó uno, la story que
  // quiere es ésa y no las placas que la acompañan. Las dos opciones —reel y
  // story— quedan a la vista, así que la persona elige; son publicaciones
  // distintas (el reel queda en la grilla, la story se va en 24 horas) y
  // elegir por ella sería adivinar.
  if (videos.length) {
    opciones.push({ tipo: "story", urls: [videos[0]], piezas: 1 });
  } else if (verticales.length) {
    opciones.push({
      tipo: "story",
      urls: verticales.map((i) => i.url),
      piezas: verticales.length,
    });
  }

  if (!opciones.length) {
    return json({
      error: "Este diseño no tiene ninguna pieza que Instagram acepte.",
      codigo: "sin_piezas",
    }, 409);
  }

  // ── Cuál de las opciones ────────────────────────────────────────────────
  const pedido = String(cuerpo.tipo || "").trim().toLowerCase();
  let elegida = opciones[0];
  if (pedido) {
    const hallada = opciones.find((o) => o.tipo === pedido);
    if (!hallada) {
      return json({
        error: `Este diseño no tiene una pieza para publicar como ${pedido}.`,
        codigo: "tipo_no_disponible",
        opciones: opciones.map((o) => ({ tipo: o.tipo, piezas: o.piezas })),
      }, 409);
    }
    elegida = hallada;
  } else if (opciones.length > 1) {
    // Una vertical no entra en el feed y una placa cuadrada no es una story:
    // son publicaciones distintas y las dos son razonables. Elegir por la
    // persona acá sería adivinar cuál de las dos quería.
    return json({
      error: "Este diseño tiene piezas de más de un tipo. Preguntale a la " +
             "persona cuál quiere publicar y volvé a llamar con `tipo`.",
      codigo: "elegir_tipo",
      opciones: opciones.map((o) => ({ tipo: o.tipo, piezas: o.piezas })),
    }, 409);
  }

  // ── El tope por hora ────────────────────────────────────────────────────
  const desde = new Date(Date.now() - 3600_000).toISOString();
  const rc = await fetch(
    `${base}/rest/v1/publicaciones?creado_en=gte.${desde}&select=id`,
    { headers: { ...cab, Prefer: "count=exact", Range: "0-0" } });
  const total = Number((rc.headers.get("content-range") || "/0").split("/")[1]);
  if (total >= MAX_POR_HORA) {
    return json({
      error: `Se llegó al tope de ${MAX_POR_HORA} publicaciones por hora.`,
    }, 429);
  }

  // ── Cuándo ──────────────────────────────────────────────────────────────
  let cuando = new Date();
  if (cuerpo.publicar_en) {
    const t = new Date(String(cuerpo.publicar_en));
    if (isNaN(t.getTime())) {
      return json({ error: "La fecha de publicación no se entiende." }, 400);
    }
    if (t.getTime() < Date.now() - 60_000) {
      return json({
        error: "Esa fecha ya pasó. Elegí una futura o publicá ahora.",
      }, 400);
    }
    cuando = t;
  }

  // Instagram ignora el pie de foto en las stories: mandarlo sería prometerle
  // a la persona un texto que nadie va a leer.
  // El caption pasa por `caption_de` venga de donde venga. Si lo manda quien
  // llama, tampoco se publica tal cual: más de una vez el agente mandó el
  // `copy.txt` completo creyendo que era el texto del posteo.
  const caption = elegida.tipo === "story"
    ? ""
    : caption_de(String(cuerpo.caption ?? d.copy ?? "")).slice(0, 2200);

  // Una secuencia de stories son varias publicaciones, una por pieza: en
  // Instagram cada story es un posteo suyo. El resto es una sola fila.
  const filas = elegida.tipo === "story"
    ? elegida.urls.map((u) => ({ tipo: "story", urls: [u], caption: "" }))
    : [{ tipo: elegida.tipo, urls: elegida.urls, caption }];

  const nuevas = filas.map((f) => ({
    ...f,
    diseno_id,
    estado: "programado",
    publicar_en: cuando.toISOString(),
    ...(usuario ? { user_id: usuario } : {}),
  }));

  const r = await fetch(`${base}/rest/v1/publicaciones`, {
    method: "POST",
    headers: { ...cab, Prefer: "return=representation" },
    body: JSON.stringify(nuevas),
  });
  if (!r.ok) {
    console.error("insert", r.status, (await r.text()).slice(0, 300));
    return json({ error: "no pude registrar la publicación" }, 500);
  }
  const creadas = await r.json();

  const ahora = cuando.getTime() <= Date.now() + 60_000;
  return json({
    diseno_id,
    tipo: elegida.tipo,
    cuenta: cuenta.usuario || null,
    publicaciones: creadas.map((f: any) => ({ id: f.id, tipo: f.tipo })),
    caption: caption || null,
    // El worker corre cada minuto, así que «ahora» quiere decir «dentro del
    // próximo minuto». Decirlo evita que la persona apriete dos veces.
    cuando: ahora ? "en menos de un minuto" : cuando.toISOString(),
    // Que se haya encolado no es que se haya publicado. Meta puede rechazar
    // la pieza, y eso recién se sabe cuando el worker la sube.
    mensaje: ahora
      ? "Queda en cola y sale en menos de un minuto. Confirmá con " +
        "estado_publicacion antes de darlo por publicado."
      : "Queda programado. Confirmá con estado_publicacion cuando llegue la hora.",
  });
});
