// Publicar en Instagram una pieza que YA existe, desde el chat de Asistime.
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
//   1. **Sólo publica piezas de un diseño propio.** Nunca una URL suelta. Un
//      agente al que se le puede dictar la URL es un agente al que cualquiera
//      le publica lo que quiera en la cuenta del cliente.
//   2. **Un diseño no se publica dos veces.** Si ya hay una publicación en
//      curso o publicada, contesta 409 con los datos de esa. Sin esto, que el
//      modelo llame dos veces —que llama— duplica el posteo.
//   3. **Falla temprano y en voz alta.** Si no hay cuenta de Instagram, o el
//      diseño no está listo, o la pieza no entra en el feed, lo dice ahora y
//      no dentro de veinte minutos en una fila que nadie mira.
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

/** Ancho y alto de un PNG, sin bajar el archivo entero.
 *
 * Las medidas están en los primeros 24 bytes, así que un Range alcanza. Se
 * mide en vez de adivinar por el nombre porque el nombre lo escribe el agente
 * y puede decir cualquier cosa; los píxeles no mienten. */
async function medir(url: string): Promise<[number, number] | null> {
  try {
    const r = await fetch(url, { headers: { Range: "bytes=0-33" } });
    if (!r.ok) return null;
    const b = new Uint8Array(await r.arrayBuffer());
    if (b.length < 24 || b[0] !== 0x89 || b[1] !== 0x50) return null;
    const dv = new DataView(b.buffer, b.byteOffset, b.byteLength);
    return [dv.getUint32(16), dv.getUint32(20)];
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

  const diseno_id = String(cuerpo.diseno_id || "").trim();
  if (!diseno_id) return json({ error: "falta diseno_id" }, 400);

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
  if (verticales.length) {
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
