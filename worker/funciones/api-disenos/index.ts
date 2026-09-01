// La puerta de entrada para pedir un diseño desde afuera de la app.
//
// La usa el chat de Asistime a través de una tool. Es deliberadamente angosta:
// **sólo sabe hacer dos cosas**, crear un pedido y contar cómo va.
//
// ── Por qué existe, en vez de que la tool escriba en la base ──────────────
//
// La tool de Asistime no tiene dónde guardar secretos: lo que use queda a la
// vista en su propio código. Si le diéramos la `service_role` del cliente,
// esa clave —que lee y escribe TODO, incluido el token de Instagram— quedaría
// en la configuración de una plataforma, visible para cualquiera que abra la
// herramienta a editarla.
//
// Con esta función, lo que queda expuesto es una clave que sólo sirve para
// encargar diseños en UNA base. Si se filtra, lo peor que puede pasar es que
// alguien encargue piezas —que además consumen saldo y quedan registradas—, no
// que lea datos ni borre nada. Y se revoca cambiando un secreto, sin tocar la
// base.
//
// ── Quién espera, y por qué acá ──────────────────────────────────────────
//
// Un diseño tarda de 2 a 4 minutos: Chromium levanta, renderiza, y si hay reel
// además corre ffmpeg. Eso es más de lo que aguanta cualquier llamada, así que
// `POST` devuelve el id al instante y `GET` cuenta cómo va.
//
// Pero el `GET` **espera un rato adentro** antes de contestar «todavía no», y
// eso importa más de lo que parece: la espera tiene que vivir ACÁ, en Deno,
// porque el sandbox donde corren las tools de Asistime **no la puede hacer**.
// Una tool que hace `await new Promise(r => setTimeout(r, 8000))` no duerme y
// sigue: se muere ahí. Y se muere sólo cuando la pieza NO estaba lista, que es
// justamente el caso para el que se había escrito la espera — así que andaba
// siempre que no hiciera falta.
//
// Se descubrió el 27/8/2026, en Clínica: una consulta que llegó nueve segundos
// antes de que la pieza terminara, y el chat contestó un error por una placa
// que había salido bien.

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-api-clave",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
};

// Tope de pedidos por hora. No es una defensa contra un atacante decidido: es
// el límite que hace que una tool mal configurada —o un bucle en el chat— no
// se coma el saldo del cliente en una tarde.
const MAX_POR_HORA = 20;

const FORMATOS = ["post", "vertical", "story", "reel", "video",
                  "carrusel", "secuencia", "pdf"];

// Cuántas fotos puede mandar una persona en un pedido, y cuánto puede pesar
// cada una. Una foto de celular pesa entre 2 y 5 MB; 12 deja margen para una
// cámara buena sin abrir la puerta a que alguien nos mande un video disfrazado.
const MAX_FOTOS = 4;
const MAX_BYTES = 12 * 1024 * 1024;

const TIPOS: Record<string, string> = {
  jpg: "image/jpeg", png: "image/png",
  webp: "image/webp", gif: "image/gif",
};

// Cuánto espera el GET a que la pieza esté antes de contestar «todavía no».
// El tope de la tool que llama es de 90 segundos: 55 deja margen de sobra y,
// encadenando tres o cuatro consultas, cubre los 2 a 4 minutos que tarda una
// pieza sin que el chat conteste nunca un error.
const ESPERA_MAX_MS = 55_000;
const ESPERA_PASO_MS = 4_000;

const dormir = (ms: number) => new Promise((r) => setTimeout(r, ms));

// La forma de una foto decide más que sus medidas: si entra en un post sin
// comerse media escena, o si sólo sirve para story. El agente elige mejor
// leyendo «vertical» que leyendo 1200x1599.
function forma(ancho?: number, alto?: number): string {
  if (!ancho || !alto) return "desconocida";
  const r = ancho / alto;
  if (r > 1.15) return "apaisada";
  if (r < 0.87) return "vertical";
  return "cuadrada";
}

function json(cuerpo: unknown, status = 200) {
  return new Response(JSON.stringify(cuerpo), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

// ── Traer la foto que mandó la persona ───────────────────────────────────
//
// La URL que da el chat es de otra plataforma y puede estar firmada por unos
// minutos. El worker la busca después —a veces bastante después, si hay cola—
// y para entonces puede no existir. Por eso la foto se COPIA al Storage del
// cliente ahora, y lo que se guarda en el pedido es nuestra copia.

const TD = new TextDecoder();

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
    // Se sacan sólo los trozos de metadatos. Los demás quedan, incluido
    // `tRNS` y el canal alfa: un logo sin transparencia no sirve para nada.
    if (!fuera.has(tipo)) partes.push(b.subarray(i, fin));
    i = fin;
    if (tipo === "IEND") break;
  }
  return unir(partes);
}

function limpiarWebp(b: Uint8Array): Uint8Array | null {
  const partes = [b.subarray(0, 12)];
  let flags = -1;            // dónde cae el byte de banderas en la salida
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

  // Un WebP extendido lleva un chunk `VP8X` cuyo primer byte declara QUÉ trae
  // el archivo: ICC, alfa, EXIF, XMP, animación. Sacar el chunk de EXIF sin
  // bajar su bandera deja un archivo que dice tener metadatos que ya no están.
  //
  // Muchos decodificadores lo perdonan —Pillow lo abre sin chistar, Chromium
  // también— pero los estrictos rechazan la imagen ENTERA. Ahí no se pierde el
  // metadato: se pierde la foto. Se descubrió del lado de las plantillas, donde
  // la foto termina en un agente que la MIRA: llegó como «an image in the
  // conversation could not be processed and was removed» y el diseño se hizo
  // sin ella.
  //
  // Acá el efecto es más callado, y por eso peor: Chromium la dibuja igual, así
  // que las piezas salieron bien todo este tiempo y nadie tenía por qué
  // sospechar. Pero el archivo guardado está mal, y cualquier cosa que lo lea
  // con un decodificador estricto lo va a descartar sin decir por qué.
  //
  // Los chunks EXIF y XMP nunca se copian, así que las dos banderas van
  // SIEMPRE en cero. Ponerlas por lo que el archivo tiene al final —y no por
  // lo que esta pasada sacó— es además lo que cura los que ya estaban mal:
  // volver a pasarlos por acá los deja coherentes aunque el chunk lo haya
  // sacado otro.
  if (flags >= 0 && flags < salida.length) {
    salida[flags] &= ~(0x08 | 0x04);
  }

  // El encabezado RIFF declara el tamaño total: si se sacaron trozos hay que
  // corregirlo, o el archivo queda diciendo que pesa más de lo que pesa.
  new DataView(salida.buffer).setUint32(4, salida.length - 8, true);
  return salida;
}

/** Saca todo lo que la foto cuenta sobre quién la sacó y dónde.
 *
 * Una foto de celular trae las coordenadas del lugar donde se tomó, y el
 * bucket es de lectura pública. En la pieza publicada eso no sobrevive
 * —Chromium la vuelve a dibujar— pero el original sí queda.
 *
 * No re-comprime: mueve bytes, no píxeles. Si el archivo no se entiende, se
 * guarda como vino: mejor una foto con metadatos que ninguna foto. */
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
// ── Un link de Google Drive no es una imagen ──────────────────────────────
//
// Lo que Drive le da a una persona cuando comparte una foto es
// `drive.google.com/file/d/<id>/view`, y eso NO es la foto: es una PÁGINA que
// muestra la foto. Bajarla trae HTML, o un 401 si además hay que iniciar
// sesión. El 1/9/2026 alguien pidió un carrusel con cinco fotos de una carpeta
// de Drive y las cinco rebotaron; la respuesta razonable del agente fue pedirle
// que las descargara y las subiera de nuevo a mano, que es exactamente el
// trabajo que esta herramienta existe para no hacer.
//
// Drive sí tiene direcciones que devuelven los bytes. Se prueban en orden:
//
//   1. `uc?export=download` → el archivo original, tal cual se subió;
//   2. `thumbnail?sz=w2000`  → un JPG que Drive arma al vuelo. Aguanta casos
//      donde la primera contesta con la pantalla de «no pudimos analizar este
//      archivo», que pasa con los archivos grandes.
//
// **Lo que esto NO arregla:** una carpeta privada. Si el archivo no está
// compartido como «cualquiera con el enlace», Drive no lo entrega a nadie que
// no haya iniciado sesión, y este servidor nunca la inicia. Ahí no hay truco
// posible y lo único honesto es decirlo con esas palabras.
function idDeDrive(u: string): string | null {
  let url: URL;
  try { url = new URL(u); } catch { return null; }
  const h = url.hostname.toLowerCase();
  if (h !== "drive.google.com" && h !== "docs.google.com") return null;
  // Las dos formas en que Drive pone el id en la ruta: `/file/d/<id>/view`,
  // que es la que copia una persona, y `/d/<id>` de los documentos.
  const enLaRuta = url.pathname.match(/\/(?:file\/)?d\/([A-Za-z0-9_-]{20,})/);
  if (enLaRuta) return enLaRuta[1];
  const q = url.searchParams.get("id");
  return q && /^[A-Za-z0-9_-]{20,}$/.test(q) ? q : null;
}

/** Las direcciones a probar para UNA foto, en orden. */
function candidatas(u: string): string[] {
  const id = idDeDrive(u);
  if (!id) return [u];
  return [
    `https://drive.google.com/uc?export=download&id=${id}`,
    `https://drive.google.com/thumbnail?id=${id}&sz=w2000`,
  ];
}

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

  // Comparación de largo constante. Con `===` el tiempo de respuesta varía
  // según cuántos caracteres coinciden, y eso alcanza para adivinar la clave
  // a fuerza de intentos.
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

  // ── Cómo va un pedido ───────────────────────────────────────────────────
  if (req.method === "GET") {
    const url0 = new URL(req.url);

    // ── Qué fotos hay en el banco ─────────────────────────────────────────
    //
    // Vive acá, y no en una función aparte, porque es la pregunta que hay que
    // contestar ANTES de encargar una pieza: «¿qué fotos tenemos?». Sin esto,
    // pedirle al agente que elija una del banco es pedirle que adivine una
    // clave. Y una clave inventada no falla ruidosamente: el diseñador elige
    // otra foto y la pieza sale bien, pero con la que él quiso — que es la
    // peor forma de fallar, porque nadie se entera.
    if (url0.pathname.endsWith("/banco")) {
      const r = await fetch(
        `${base}/rest/v1/fotos?activa=eq.true` +
        `&select=clave,descripcion,etiquetas,ancho,alto&order=clave&limit=100`,
        { headers: cab },
      );
      if (!r.ok) return json({ error: "no pude leer el banco de fotos" }, 502);
      const filas = await r.json();
      return json({
        total: filas.length,
        fotos: filas.map((f: any) => ({
          clave: f.clave,
          descripcion: f.descripcion || "Sin descripción.",
          usar_para: (f.etiquetas || []).join(", ") || "uso general",
          forma: forma(f.ancho, f.alto),
        })),
      });
    }

    const id = url0.searchParams.get("id");
    if (!id) return json({ error: "falta el parámetro id" }, 400);
    const esperar = url0.searchParams.get("esperar") !== "no";

    const armar = (d: any) => {
      const listo = d.estado === "listo";
      return {
        id: d.id,
        estado: d.estado,
        listo,
        // `terminado` distingue «ya no va a cambiar» de «sigue trabajando»,
        // que es lo único que el chat necesita para decidir si vuelve a
        // preguntar.
        terminado: listo || d.estado === "error",
        titulo: d.titulo || null,
        imagenes: d.urls || [],
        documentos: (d.documentos || []).map((x: any) => x.url),
        videos: (d.videos || []).map((x: any) => x.url),
        copy: d.copy || null,
        mensaje: d.mensaje_agente || null,
        // Cuánto hace que espera. Un pedido puede quedarse en `pendiente` para
        // siempre —el worker caído, la cuenta sin saldo— y desde afuera eso se
        // ve igual que «está trabajando». Con este número, quien pregunta puede
        // distinguir «falta poco» de «acá pasó algo».
        esperando_seg: d.creado_en
          ? Math.round((Date.now() - new Date(d.creado_en).getTime()) / 1000)
          : null,
      };
    };

    const hasta = Date.now() + (esperar ? ESPERA_MAX_MS : 0);
    for (;;) {
      const r = await fetch(
        `${base}/rest/v1/disenos?id=eq.${encodeURIComponent(id)}` +
        `&select=id,estado,titulo,urls,documentos,videos,copy,mensaje_agente,creado_en&limit=1`,
        { headers: cab },
      );
      if (!r.ok) return json({ error: "no pude consultar el pedido" }, 502);
      const [d] = await r.json();
      if (!d) return json({ error: "no existe ese pedido" }, 404);

      const cuerpo = armar(d);
      if (cuerpo.terminado || Date.now() >= hasta) return json(cuerpo);
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

  const mensaje = String(cuerpo.mensaje || "").trim();
  if (mensaje.length < 10) {
    return json({
      error: "El pedido está vacío o es demasiado corto. Contame qué tiene " +
             "que comunicar la pieza.",
    }, 400);
  }

  const formatos = (Array.isArray(cuerpo.formatos) ? cuerpo.formatos : [])
    .filter((f: string) => FORMATOS.includes(f));
  if (!formatos.length) formatos.push("post");

  // ── El saldo ───────────────────────────────────────────────────────────
  //
  // Se mira acá y no sólo en el worker por una razón de honestidad: sin este
  // corte, un pedido sin saldo se acepta, queda en `pendiente` y el chat le
  // dice a la persona «ya te lo preparo» por una pieza que no va a salir
  // nunca. Es mejor decirle que no en el momento.
  //
  // `mi_cuenta` no existe en los clientes que todavía no tienen cobro: un 404
  // significa «este cliente no paga por consumo», y ahí no se frena nada.
  const rs = await fetch(`${base}/rest/v1/mi_cuenta?select=saldo_usd&limit=1`,
                         { headers: cab });
  if (rs.ok) {
    const [cuenta] = await rs.json();
    const saldo = Number(cuenta?.saldo_usd ?? 0);
    if (saldo < 1.5) {
      return json({
        error: "Se agotó el saldo de la cuenta. Apenas la recargues, " +
               "volvé a pedir el diseño y sale en minutos.",
        codigo: "sin_saldo",
      }, 402);
    }
  }

  // ── El tope por hora ───────────────────────────────────────────────────
  const desde = new Date(Date.now() - 3600_000).toISOString();
  const rc = await fetch(
    `${base}/rest/v1/disenos?creado_en=gte.${desde}&select=id`,
    { headers: { ...cab, Prefer: "count=exact", Range: "0-0" } },
  );
  const total = Number((rc.headers.get("content-range") || "/0").split("/")[1]);
  if (total >= MAX_POR_HORA) {
    return json({
      error: `Se llegó al tope de ${MAX_POR_HORA} pedidos por hora. ` +
             `Probá de nuevo más tarde.`,
    }, 429);
  }

  // ── Las fotos que mandó la persona ────────────────────────────────────
  //
  // Se hace ANTES de crear el pedido a propósito. Si una foto no se puede
  // traer, el chat se entera ahora y puede pedirla de nuevo — en vez de que
  // la pieza salga dos minutos después con una foto del banco y nadie sepa
  // por qué no se usó la que mandaron.
  const copiar = async (u: string, n: number) => {
    if (!direccion_valida(u)) throw new Error("no es una dirección válida");

    // Se prueban las direcciones en orden y gana la primera que traiga una
    // imagen de verdad. Para una URL normal la lista tiene una sola.
    let crudo: Uint8Array<ArrayBuffer> | null = null;
    let fmt: string | null = null;
    let ultimo = "";
    for (const c of candidatas(u)) {
      let r: Response;
      try {
        r = await fetch(c, { signal: AbortSignal.timeout(20000) });
      } catch (e) {
        ultimo = `no pude llegar a la dirección (${e})`;
        continue;
      }
      if (!r.ok) { ultimo = `el servidor contestó ${r.status}`; continue; }
      const bytes = new Uint8Array(await r.arrayBuffer());
      if (bytes.length > MAX_BYTES) throw new Error("pesa más de 12 MB");
      const f = formato(bytes);
      if (!f) {
        ultimo = "no es una imagen que sirva (mandala en JPG o PNG)";
        continue;
      }
      crudo = bytes;
      fmt = f;
      break;
    }
    if (!crudo || !fmt) {
      // Si venía de Drive, el motivo casi siempre es el mismo y se puede
      // arreglar en diez segundos. Decirlo con esas palabras vale más que
      // repetir el código de error.
      if (idDeDrive(u)) {
        throw new Error(
          "es un archivo de Google Drive que no está compartido. Abrí la " +
          "carpeta en Drive → Compartir → «Cualquier persona con el enlace» " +
          "→ Lector, y volvé a mandarme el mismo link. No hace falta que " +
          "descargues nada",
        );
      }
      throw new Error(ultimo || "no la pude bajar");
    }
    const ruta = `adjuntos/${usuario || "asistime"}/${crypto.randomUUID()}.${fmt}`;
    const up = await fetch(`${base}/storage/v1/object/disenos/${ruta}`, {
      method: "POST",
      headers: {
        apikey: llave,
        Authorization: `Bearer ${llave}`,
        "Content-Type": TIPOS[fmt],
      },
      body: limpiar(crudo, fmt),
    });
    if (!up.ok) throw new Error("no la pude guardar");
    return {
      url: `${base}/storage/v1/object/public/disenos/${ruta}`,
      nombre: `foto-${n}.${fmt}`,
    };
  };

  const adjuntos: { url: string; nombre: string }[] = [];
  const entrantes = Array.isArray(cuerpo.fotos) ? cuerpo.fotos.slice(0, MAX_FOTOS) : [];
  for (let i = 0; i < entrantes.length; i++) {
    try {
      adjuntos.push(await copiar(String(entrantes[i]), i + 1));
    } catch (e) {
      return json({
        error: `No pude usar la foto ${i + 1}: ${(e as Error).message}. ` +
               `Pedile a la persona que la mande de nuevo.`,
        codigo: "foto_no_sirve",
      }, 400);
    }
  }

  // El logo del socio pasa por lo mismo, y por la misma razón: una URL
  // prestada que se vence deja la pieza de convenio sin el logo de la empresa,
  // que es justamente lo único que esa pieza tiene de propio.
  let logo = "";
  if (cuerpo.logo_socio) {
    try {
      logo = (await copiar(String(cuerpo.logo_socio), 0)).url;
    } catch (e) {
      return json({
        error: `No pude usar el logo: ${(e as Error).message}.`,
        codigo: "logo_no_sirve",
      }, 400);
    }
  }

  const fila: Record<string, unknown> = {
    mensaje: mensaje.slice(0, 4000),
    formatos,
    estado: "pendiente",
    quien: String(cuerpo.quien || "Asistime").slice(0, 120),
  };
  if (usuario) fila.user_id = usuario;
  if (cuerpo.sede) fila.sede = String(cuerpo.sede).slice(0, 120);
  if (Array.isArray(cuerpo.fotos_elegidas)) {
    fila.fotos_elegidas = cuerpo.fotos_elegidas.slice(0, 10).map(String);
  }
  if (adjuntos.length) fila.adjuntos = adjuntos;
  if (logo) fila.logo_socio = logo;

  const r = await fetch(`${base}/rest/v1/disenos`, {
    method: "POST",
    headers: { ...cab, Prefer: "return=representation" },
    body: JSON.stringify(fila),
  });
  if (!r.ok) {
    console.error("insert", r.status, (await r.text()).slice(0, 300));
    return json({ error: "no pude registrar el pedido" }, 500);
  }
  const [creado] = await r.json();

  return json({
    id: creado.id,
    estado: "pendiente",
    formatos,
    // Que el chat pueda decir «me quedé con tus dos fotos». Si la persona
    // mandó tres y llegaron dos, tiene derecho a enterarse ahora.
    fotos_recibidas: adjuntos.length,
    // El chat necesita saber cuánto esperar antes de volver a preguntar. Un
    // reel tarda bastante más que una placa.
    demora_estimada_seg: formatos.some((f: string) =>
      ["video", "pdf", "carrusel", "secuencia"].includes(f)) ? 240 : 150,
    mensaje: "Pedido tomado. Consultá el estado en un par de minutos.",
  });
});
