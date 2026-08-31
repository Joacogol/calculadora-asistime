// La puerta de entrada para pedir un REEL desde el chat de Asistime.
//
// ── Dos formas de pedirlo, con precios que no se parecen ──────────────────
//
// Con `foto`: un modelo de video INVENTA el clip. Son miles de créditos y unos
// cinco minutos. Es lo que existía desde el principio.
//
// Con `clips` + `guion`: el material YA existe —lo filmó el cliente, lo eligió
// una persona— y el motor lo corta, lo pega, lo encuadra en 9:16 y le pone los
// subtítulos con la tipografía de la marca. **No gasta un solo crédito** y
// tarda menos de un minuto.
//
// Son excluyentes a propósito: entre las dos hay tres órdenes de magnitud de
// diferencia en plata, así que un pedido que trae las dos se rechaza en vez de
// elegir una en silencio.
//
// Hermana de `api-disenos`, y por las mismas razones: la tool no tiene dónde
// guardar secretos, así que lo que queda expuesto en su código es una clave que
// sólo sirve para encargar piezas en UNA base. Si se filtra, lo peor que pasa
// es que alguien encargue reels —que gastan créditos y quedan registrados—, no
// que lea datos ni borre nada.
//
// ── Por qué acá tampoco se espera el reel entero ─────────────────────────
//
// Generar el video son cuatro minutos. Además del timeout hay una razón mejor:
// la tool corre DENTRO del turno del agente, así que esperar todo eso deja el
// chat mudo, y si la conversación se corta en el medio el pedido se pierde con
// ella.
//
// `POST` anota y devuelve el id al instante. `GET` cuenta cómo va — esperando
// hasta un minuto adentro, que no cubre los cinco pero hace que cada consulta
// valga por un minuto en vez de por un instante.

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-api-clave",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
};

// Cuántos reels se pueden pedir por hora. Es un freno contra un bucle del chat,
// NO el control de gasto: el que corta por plata es `creditos_maximos` del
// `marca.json`, que mira los créditos de CADA pieza. El techo mensual que
// había se sacó el 28/8/2026 —cuánto gasta el cliente en un mes es decisión
// suya—, así que hoy este tope por hora es el único límite por cantidad.
//
// Empezó en 3 y frenaba antes de que nadie terminara de probar. Lo importante
// es que un tope por hora bajo no ahorra un peso —el que pide doce reels en
// una hora los quería— y en cambio corta una conversación con una persona
// esperando del otro lado.
//
// Se puede cambiar sin tocar código con la variable `REELS_POR_HORA` en
// Supabase. En 0 no hay tope por hora y manda sólo el tope de créditos.
const MAX_POR_HORA = Number(Deno.env.get("REELS_POR_HORA") ?? 12);

// Cuántos clips propios se pueden pegar en un reel. Cada uno se baja entero y
// se recodifica, así que el costo es tiempo de montaje, no plata. Doce tramos
// en 90 segundos son siete segundos y medio cada uno: más que eso ya no es un
// reel editado, es una lista de cortes.
const MAX_CLIPS = Number(Deno.env.get("CLIPS_POR_REEL") ?? 12);

// Cuánto espera el GET a que el reel esté antes de contestar «todavía no».
// Un reel tarda unos cinco minutos, así que la espera no lo cubre entero: lo
// que hace es que cada consulta valga por un minuto en vez de por un instante.
//
// La espera vive ACÁ y no en la tool de Asistime porque el sandbox de las
// tools no sabe dormir: un `setTimeout` no lo suspende, lo mata. Ver la nota
// larga en `api-disenos`.
const ESPERA_MAX_MS = 55_000;
const ESPERA_PASO_MS = 5_000;

const dormir = (ms: number) => new Promise((r) => setTimeout(r, ms));

const json = (b: unknown, s = 200) =>
  new Response(JSON.stringify(b), {
    status: s,
    headers: { ...CORS, "Content-Type": "application/json" },
  });

/** ¿Es una URL que el worker va a poder bajar? Sirve para la foto y para los clips.
 *
 *  Se valida acá y no en el worker porque acá el error todavía le puede llegar
 *  a una persona que puede arreglarlo. Cuatro minutos después, cuando el worker
 *  descubra que la foto no existe, ya se gastaron los créditos.
 */
function urlDescargable(u: string): boolean {
  try {
    const url = new URL(u);
    if (url.protocol !== "https:") return false;
    const h = url.hostname.toLowerCase();
    // Nada de direcciones internas: esta función corre con la service_role y
    // una URL a `localhost` o a una IP privada la convertiría en un ariete
    // contra la red de adentro.
    if (h === "localhost" || h.endsWith(".localhost") || h === "::1") return false;
    if (/^(10\.|127\.|169\.254\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(h)) return false;
    return true;
  } catch {
    return false;
  }
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

  const esperada = Deno.env.get("API_CLAVE");
  if (!esperada) return json({ error: "falta configurar API_CLAVE" }, 500);

  const dada = req.headers.get("x-api-clave") || "";
  if (dada !== esperada) {
    return json({ error: "clave inválida", codigo: "clave_invalida" }, 401);
  }

  const base = Deno.env.get("SUPABASE_URL")!;
  const llave = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const usuario = Deno.env.get("USUARIO_ID") || null;
  const cab = {
    apikey: llave,
    Authorization: `Bearer ${llave}`,
    "Content-Type": "application/json",
  };
  const tabla = `${base}/rest/v1/reels`;

  // ── Cómo va un pedido ──────────────────────────────────────────────────
  if (req.method === "GET") {
    const url0 = new URL(req.url);
    const id = url0.searchParams.get("id");
    if (!id) return json({ error: "falta id" }, 400);
    const esperar = url0.searchParams.get("esperar") !== "no";

    const hasta = Date.now() + (esperar ? ESPERA_MAX_MS : 0);
    for (;;) {
      const r = await fetch(
        `${tabla}?id=eq.${encodeURIComponent(id)}&select=id,estado,url,notas,` +
          `creditos_estimados,creado_en,titulo`,
        { headers: cab },
      );
      const filas = await r.json();
      if (!Array.isArray(filas) || !filas.length) {
        return json({ error: "no existe", codigo: "no_existe" }, 404);
      }
      const f = filas[0];
      const terminado = ["listo", "error", "rechazado"].includes(f.estado);
      const cuerpo = {
        id: f.id,
        estado: f.estado,
        listo: f.estado === "listo",
        terminado,
        url: f.url || null,
        titulo: f.titulo || null,
        creditos: f.creditos_estimados || null,
        mensaje: f.notas || null,
        esperando_seg: Math.round(
          (Date.now() - new Date(f.creado_en).getTime()) / 1000,
        ),
      };
      if (terminado || Date.now() >= hasta) return json(cuerpo);
      await dormir(ESPERA_PASO_MS);
    }
  }

  if (req.method !== "POST") return json({ error: "método no permitido" }, 405);

  // ── Anotar un pedido ───────────────────────────────────────────────────
  let c: Record<string, unknown>;
  try {
    c = await req.json();
  } catch {
    return json({ error: "cuerpo inválido" }, 400);
  }

  const mensaje = String(c.mensaje ?? "").trim();
  const foto = String(c.foto ?? "").trim();
  const clips = Array.isArray(c.clips) ? c.clips : [];
  const guion = (c.guion && typeof c.guion === "object") ? c.guion as Record<string, unknown> : null;

  if (mensaje.length < 10) {
    return json({ error: "el pedido está vacío", codigo: "pedido_incompleto" }, 400);
  }

  // ── Hay dos formas de pedir un reel y son excluyentes ────────────────────
  //
  //   con `clips`  → el material YA existe y sólo hay que editarlo. No gasta
  //                  un crédito: no interviene ningún modelo de video.
  //   con `foto`   → un modelo inventa el video a partir de esa foto. Cuesta
  //                  miles de créditos.
  //
  // La diferencia de precio entre las dos es de tres órdenes de magnitud, así
  // que mandar las dos no se resuelve eligiendo una en silencio: se rechaza y
  // se pregunta. Adivinar acá es adivinar con la plata del cliente.
  if (clips.length && foto) {
    return json({
      error: "llegaron `clips` y `foto` juntos, y son dos pedidos distintos: " +
        "con `clips` se EDITA material que ya existe y no cuesta créditos; con " +
        "`foto` un modelo INVENTA el video y cuesta miles. Mandá uno solo.",
      codigo: "clips_y_foto",
    }, 400);
  }

  if (clips.length) {
    if (clips.length > MAX_CLIPS) {
      return json({
        error: `son ${clips.length} clips y el tope es ${MAX_CLIPS}. Cada uno se ` +
          `baja y se recodifica: más que eso no es un reel, es un problema de ` +
          `tiempo de montaje.`,
        codigo: "demasiados_clips",
      }, 400);
    }
    for (const c0 of clips) {
      const u = typeof c0 === "string" ? c0 : String((c0 as Record<string, unknown>)?.url ?? "");
      if (!urlDescargable(u)) {
        return json({
          error: `«${u.slice(0, 80)}» no sirve como clip: tiene que ser una URL ` +
            `https pública que se pueda descargar.`,
          codigo: "clip_invalido",
        }, 400);
      }
    }
    // El guion se chequea por encima acá y a fondo en el worker, que es el que
    // tiene los archivos y sabe cuánto dura cada uno. Lo de acá es lo que se
    // puede saber sin bajar nada, y vale la pena: este error le llega a alguien
    // que lo puede arreglar en el mismo turno.
    const tramos = Array.isArray(guion?.tramos) ? guion!.tramos as unknown[] : [];
    if (!tramos.length) {
      return json({
        error: "faltan los tramos del guion: con los clips solos el motor no sabe " +
          "qué pedazo de cada uno usar. Cada tramo lleva `archivo`, `desde` y " +
          "`hasta`, en segundos del material original.",
        codigo: "falta_el_guion",
      }, 400);
    }
  } else {
    if (!foto) {
      return json({
        error: "un reel se arma A PARTIR de una foto, o EDITANDO clips que ya " +
          "existen. Sin una cosa ni la otra no hay reel. La foto puede ser una " +
          "del banco de la marca, una que hayan mandado en el chat, o una " +
          "inventada con `crear_foto`; los clips son videos que mandaron.",
        codigo: "falta_la_foto",
      }, 400);
    }
    if (!urlDescargable(foto)) {
      return json({
        error: "la foto tiene que ser una URL https pública que se pueda descargar",
        codigo: "foto_invalida",
      }, 400);
    }
  }

  const desde = new Date(Date.now() - 3600_000).toISOString();
  const rc = await fetch(
    `${tabla}?creado_en=gte.${desde}&estado=not.in.(rechazado,error)&select=id`,
    { headers: { ...cab, Prefer: "count=exact" } },
  );
  const recientes = (await rc.json()) as unknown[];
  if (MAX_POR_HORA > 0 && Array.isArray(recientes) &&
      recientes.length >= MAX_POR_HORA) {
    return json({
      error: `ya se pidieron ${recientes.length} reels en la última hora, que es el ` +
        `tope. Cada uno cuesta créditos: si de verdad hacen falta más, hay que ` +
        `subir el tope a propósito (variable REELS_POR_HORA).`,
      codigo: "tope_por_hora",
    }, 429);
  }

  const fila: Record<string, unknown> = { mensaje, quien: c.quien ?? "Asistime" };
  if (clips.length) {
    fila.clips = clips;
    fila.guion = guion ?? {};
  } else {
    fila.foto = foto;
  }
  for (const k of ["titulo", "kicker", "bajada", "musica"]) {
    if (c[k]) fila[k] = String(c[k]).trim();
  }
  if (usuario) fila.user_id = usuario;

  const r = await fetch(tabla, {
    method: "POST",
    headers: { ...cab, Prefer: "return=representation" },
    body: JSON.stringify(fila),
  });
  if (!r.ok) {
    return json({ error: "no se pudo anotar el pedido", detalle: await r.text() }, 500);
  }
  const creada = (await r.json())[0];

  return json({
    id: creada.id,
    estado: creada.estado,
    // Montar material que ya existe es cortar y pegar: no hay que esperar a
    // ningún modelo. Decir 300 acá haría que el agente avise «esto tarda cinco
    // minutos» por algo que sale en menos de uno.
    demora_estimada_seg: clips.length ? 60 : 300,
    cuesta_creditos: !clips.length,
  }, 201);
});
