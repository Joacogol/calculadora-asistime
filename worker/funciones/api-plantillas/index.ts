// La puerta para pedir una PLANTILLA nueva desde afuera de la app.
//
// Hermana de `api-disenos`, y a propósito casi idéntica: encargar, consultar,
// confirmar. Lo que cambia es el objeto — ahí se pide una pieza, acá se pide la
// plantilla con la que después se hacen muchas piezas.
//
// ── `corrige` ────────────────────────────────────────────────────────────
//
// El mismo endpoint sirve para las dos cosas que le van a pedir: «quiero una
// plantilla para X» y «a la de torneos hacele el título más grande». Se
// distinguen por un campo: si viene `corrige` con el id de una plantilla que
// ya existe, el worker baja la última versión de esa plantilla —publicada o
// no— y la EDITA.
//
// Podría haber sido otro endpoint. Es un campo porque desde el chat las dos
// frases llegan iguales, y lo único que cambia es si nombran una plantilla que
// ya está. Que sea un campo hace que agregarlo no cambie a quien ya llamaba.
//
// ── `fotos` ──────────────────────────────────────────────────────────────
//
// Una plantilla se pide mostrando: «como ésta pero con esta foto de fondo».
// El manejo de fotos es COPIA LITERAL del de `api-disenos` —bajar, verificar
// que sea una imagen por sus bytes, sacarle los metadatos, guardarla en el
// Storage del cliente— y eso es a propósito: es el mismo problema y ya está
// resuelto ahí. Escribir una segunda versión sería garantizar que dentro de
// seis meses alguien arregle una y no la otra.
//
// ── Por qué también recibe los pedidos de motor ──────────────────────────
//
// `POST /motor` anota un pedido que NO se resuelve con una plantilla: el video,
// un formato que no existe, la estructura del carrusel. Antes eso era un mail y
// nada más — y un mail que nadie lee es un pedido perdido, además de un pedido
// que no se puede contar.
//
// Vive acá y no en una quinta función porque es la misma puerta conceptual: lo
// que entra por este endpoint son pedidos de cambiar QUÉ SABE HACER el sistema
// de diseño. Que una parte se resuelva sola —la plantilla— y la otra necesite
// código es una diferencia de implementación, no de naturaleza. Y no suma otro
// secreto que rotar.
//
// ── Por qué usa la MISMA clave que api-disenos ───────────────────────────
//
// Porque una clave más sería una deuda más. `API_CLAVE` ya está expuesta en el
// código de cuatro herramientas de Asistime y hay que rotarla; sumar una quinta
// puerta con su propio secreto significa dos rotaciones el día que se haga, y
// dos lugares donde uno de los dos queda viejo. El alcance no cambia: quien
// tenga esta clave ya podía encargar diseños en esta base.
//
// ── Por qué publicar entra por acá y no por la base ──────────────────────
//
// `publicar_plantilla` cambia TODAS las piezas que se hagan de ahí en adelante.
// Es la acción más pesada del sistema después de publicar en Instagram. Que
// pase por una función angosta —que verifica la clave y sólo sabe publicar una
// versión que ya existe— es lo que evita que un agente al que le dictan un SQL
// pueda hacer otra cosa.

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-api-clave",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
};

// Armar una plantilla cuesta una corrida del agente y varios renders. Seis por
// hora es holgado para trabajar y angosto para que un bucle en el chat no se
// coma la tarde.
const MAX_POR_HORA = 6;

// Cuántas fotos de referencia puede traer un pedido, y cuánto puede pesar cada
// una. Mismos números que en `api-disenos`.
const MAX_FOTOS = 4;
const MAX_BYTES = 12 * 1024 * 1024;

const TIPOS: Record<string, string> = {
  jpg: "image/jpeg", png: "image/png",
  webp: "image/webp", gif: "image/gif",
};

const TD = new TextDecoder();

// Cuánto espera el GET a que la plantilla esté antes de contestar «todavía
// no». La espera vive ACÁ y no en la tool de Asistime porque el sandbox de las
// tools no sabe dormir: un `setTimeout` no lo suspende, lo mata. Ver la nota
// larga en `api-disenos`.
const ESPERA_MAX_MS = 55_000;
const ESPERA_PASO_MS = 4_000;

const dormir = (ms: number) => new Promise((r) => setTimeout(r, ms));

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
//
// Todo esto es copia literal de `api-disenos`. Ver la nota de arriba.

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
  // Muchos decodificadores lo perdonan —Pillow lo abre sin chistar— pero los
  // estrictos rechazan la imagen ENTERA, y ahí no se pierde el metadato: se
  // pierde la foto. Pasó de verdad: una foto de referencia que alguien mandó
  // para una plantilla le llegó al agente como «an image in the conversation
  // could not be processed and was removed», y el diseño se hizo sin mirarla.
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

  // Comparación de largo constante, igual que en api-disenos: con `===` el
  // tiempo de respuesta varía según cuántos caracteres coinciden, y eso alcanza
  // para adivinar la clave a fuerza de intentos.
  const dada = req.headers.get("x-api-clave") || "";
  if (dada.length !== esperada.length) return json({ error: "clave inválida" }, 401);
  let iguales = 0;
  for (let i = 0; i < esperada.length; i++) {
    iguales |= dada.charCodeAt(i) ^ esperada.charCodeAt(i);
  }
  if (iguales !== 0) return json({ error: "clave inválida" }, 401);

  const base = Deno.env.get("SUPABASE_URL")!;
  const llave = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const cab = {
    apikey: llave,
    Authorization: `Bearer ${llave}`,
    "Content-Type": "application/json",
  };

  const url = new URL(req.url);
  const publicando = url.pathname.endsWith("/publicar");

  // ── Publicar una versión que ya existe ─────────────────────────────────
  if (req.method === "POST" && publicando) {
    let cuerpo: Record<string, unknown> = {};
    try { cuerpo = await req.json(); } catch { /* queda vacío */ }

    const plantilla = String(cuerpo.plantilla || "").trim();
    const version = Number(cuerpo.version || 0);
    if (!plantilla || !version) {
      return json({ error: "necesito qué plantilla y qué versión publicar" }, 400);
    }
    if (cuerpo.confirmado !== true) {
      return json({
        error: "Publicar una plantilla cambia todas las piezas que se hagan " +
               "de ahora en más. Mostrale el preview a la persona y que te lo " +
               "confirme; recién ahí volvé con confirmado: true.",
        codigo: "falta_confirmar",
      }, 428);
    }

    const r = await fetch(`${base}/rest/v1/rpc/publicar_plantilla`, {
      method: "POST", headers: cab,
      body: JSON.stringify({ p_plantilla: plantilla, p_version: version }),
    });
    if (!r.ok) {
      const detalle = await r.text();
      return json({ error: "no pude publicar esa versión", detalle: detalle.slice(0, 300) },
                   r.status === 404 ? 404 : 500);
    }
    const fila = await r.json();
    return json({
      publicada: true,
      plantilla,
      version,
      etiqueta: fila?.etiqueta ?? null,
      // Que la vuelta atrás exista y nadie la conozca es lo mismo que no
      // tenerla, así que se dice acá y no en la documentación.
      volver_atras: "Se puede volver a la versión anterior publicándola de nuevo: " +
                    "las versiones quedan todas guardadas.",
    });
  }

  // ── Anotar un pedido que necesita tocar el motor ───────────────────────
  if (req.method === "POST" && url.pathname.endsWith("/motor")) {
    let cuerpo: Record<string, unknown> = {};
    try { cuerpo = await req.json(); } catch { /* queda vacío */ }

    const resumen = String(cuerpo.resumen || "").trim();
    if (resumen.length < 10) {
      return json({
        error: "Todavía no tengo qué están pidiendo. Escribí en dos o tres " +
               "frases el cambio, con lo que ya dijo la persona — tiene que " +
               "alcanzar para que alguien que no vio el chat lo entienda.",
        codigo: "pedido_incompleto",
      }, 400);
    }

    const r = await fetch(`${base}/rest/v1/motor_pedidos`, {
      method: "POST",
      headers: { ...cab, Prefer: "return=representation" },
      body: JSON.stringify({
        resumen: resumen.slice(0, 4000),
        parte: String(cuerpo.parte || "").trim().slice(0, 300) || null,
        quien: String(cuerpo.quien || "Asistime").slice(0, 120),
      }),
    });
    if (!r.ok) {
      const detalle = await r.text();
      // Que la tabla no exista todavía no puede hacer fallar al chat: el aviso
      // por mail sigue saliendo igual, que es lo que había antes de esto.
      console.error("motor", r.status, detalle.slice(0, 300));
      return json({
        anotado: false,
        error: "no pude anotar el pedido en la base",
        detalle: detalle.slice(0, 300),
      }, 500);
    }
    const fila = (await r.json())[0];
    return json({ anotado: true, id: fila.id, estado: fila.estado }, 201);
  }

  // ── Cómo va un pedido ──────────────────────────────────────────────────
  if (req.method === "GET") {
    const id = url.searchParams.get("id");
    if (!id) return json({ error: "falta el id" }, 400);
    const esperar = url.searchParams.get("esperar") !== "no";
    const hasta = Date.now() + (esperar ? ESPERA_MAX_MS : 0);

    for (;;) {
      const r = await fetch(
        `${base}/rest/v1/plantilla_pedidos?id=eq.${encodeURIComponent(id)}` +
        `&select=id,estado,plantilla,version,preview,notas,mensaje_agente,corrige,creado_en`,
        { headers: cab });
      if (!r.ok) return json({ error: "no pude consultar el pedido" }, 500);

      const filas = await r.json();
      if (!filas.length) return json({ error: "no existe ese pedido" }, 404);
      const p = filas[0];

      const terminado = p.estado === "listo" || p.estado === "error";
      const esperando = Math.round(
        (Date.now() - new Date(p.creado_en).getTime()) / 1000);

      if (!terminado && Date.now() < hasta) {
        await dormir(ESPERA_PASO_MS);
        continue;
      }

      // Si terminó, se devuelve además el contrato: el agente necesita saber
      // qué campos tiene la plantilla nueva para poder usarla en la pieza
      // siguiente sin esperar a que el catálogo se regenere.
      let campos = null;
      if (p.estado === "listo" && p.plantilla && p.version) {
        const c = await fetch(
          `${base}/rest/v1/plantillas?plantilla=eq.${encodeURIComponent(p.plantilla)}` +
          `&version=eq.${p.version}&select=contrato`, { headers: cab });
        if (c.ok) {
          const cf = await c.json();
          campos = cf[0]?.contrato?.campos ?? null;
        }
      }

      return json({
        id: p.id,
        estado: p.estado,
        terminado,
        listo: p.estado === "listo",
        esperando_seg: esperando,
        plantilla: p.plantilla,
        version: p.version,
        corrige: p.corrige,
        preview: p.preview || [],
        campos,
        notas: p.notas,
        mensaje: p.mensaje_agente,
      });
    }
  }

  // ── Pedir una plantilla nueva ──────────────────────────────────────────
  if (req.method === "POST") {
    let cuerpo: Record<string, unknown> = {};
    try { cuerpo = await req.json(); } catch { /* queda vacío */ }

    const mensaje = String(cuerpo.mensaje || "").trim();
    const corrige = String(cuerpo.corrige || "").trim() || null;
    if (mensaje.length < 10) {
      return json({
        error: "Todavía no tengo qué tiene que resolver la plantilla. " +
               "Contame qué pieza querés poder hacer, con qué datos, y para " +
               "qué sirve.",
        codigo: "pedido_incompleto",
      }, 400);
    }

    const desde = new Date(Date.now() - 3600_000).toISOString();
    const cuenta = await fetch(
      `${base}/rest/v1/plantilla_pedidos?creado_en=gte.${desde}&select=id`,
      { headers: { ...cab, Prefer: "count=exact" } });
    const total = Number(
      (cuenta.headers.get("content-range") || "0/0").split("/")[1] || 0);
    if (total >= MAX_POR_HORA) {
      return json({
        error: `Ya se pidieron ${total} plantillas en la última hora, que es ` +
               `el tope. Probá de nuevo más tarde.`,
        codigo: "tope_por_hora",
      }, 429);
    }

    // Las fotos se copian ANTES de registrar el pedido, igual que en
    // `api-disenos` y por lo mismo: si una no se puede traer, el chat se
    // entera ahora y la puede pedir de nuevo — en vez de que la plantilla
    // salga cinco minutos después con una foto del banco y nadie sepa por qué
    // no se usó la que mandaron.
    const copiar = async (u: string, n: number) => {
      if (!direccion_valida(u)) throw new Error("no es una dirección válida");
      const rf = await fetch(u, { signal: AbortSignal.timeout(20000) });
      if (!rf.ok) throw new Error(`el servidor contestó ${rf.status}`);
      const crudo = new Uint8Array(await rf.arrayBuffer());
      if (crudo.length > MAX_BYTES) throw new Error("pesa más de 12 MB");
      const fmt = formato(crudo);
      if (!fmt) throw new Error("no es una imagen que sirva (mandala en JPG o PNG)");
      const ruta = `plantillas/referencias/${crypto.randomUUID()}.${fmt}`;
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
        nombre: `referencia-${n}.${fmt}`,
      };
    };

    const adjuntos: { url: string; nombre: string }[] = [];
    const entrantes = Array.isArray(cuerpo.fotos)
      ? cuerpo.fotos.slice(0, MAX_FOTOS) : [];
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

    const r = await fetch(`${base}/rest/v1/plantilla_pedidos`, {
      method: "POST",
      headers: { ...cab, Prefer: "return=representation" },
      body: JSON.stringify({ mensaje, corrige, adjuntos,
                             quien: cuerpo.quien || "Asistime" }),
    });
    if (!r.ok) {
      const detalle = await r.text();
      return json({ error: "no pude registrar el pedido",
                    detalle: detalle.slice(0, 300) }, 500);
    }
    const fila = (await r.json())[0];
    return json({
      id: fila.id,
      estado: fila.estado,
      corrige: fila.corrige,
      // Que el chat pueda decir «me quedé con tu foto». Si la persona mandó
      // dos y llegó una, tiene derecho a enterarse ahora.
      fotos_recibidas: adjuntos.length,
      // Armar una plantilla lleva más que una pieza: se escribe, se renderiza,
      // se mira y se corrige. Decirlo acá evita que el chat prometa un minuto.
      // Corregir una que ya existe es bastante más rápido: no hay que inventar
      // el contrato ni descubrir el diseño, sólo cambiar lo que pidieron.
      demora_estimada_seg: corrige ? 120 : 300,
    }, 201);
  }

  return json({ error: "método no soportado" }, 405);
});
