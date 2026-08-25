// La puerta de entrada para pedir un REEL desde el chat de Asistime.
//
// Hermana de `api-disenos`, y por las mismas razones: la tool no tiene dónde
// guardar secretos, así que lo que queda expuesto en su código es una clave que
// sólo sirve para encargar piezas en UNA base. Si se filtra, lo peor que pasa
// es que alguien encargue reels —que gastan créditos y quedan registrados—, no
// que lea datos ni borre nada.
//
// ── Por qué acá tampoco se espera ────────────────────────────────────────
//
// Generar el video son cuatro minutos. El sandbox de la tool corta a los 120
// segundos. Pero además hay una razón mejor que el timeout: la tool corre
// DENTRO del turno del agente, así que esperar deja el chat mudo todo ese rato
// y si la conversación se corta en el medio, el pedido se pierde con ella.
//
// `POST` anota y devuelve el id al instante. `GET` cuenta cómo va.

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-api-clave",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
};

// Un reel cuesta créditos de verdad —2.640 con la configuración de Stadium— así
// que el tope por hora es MUCHO más bajo que el de los diseños, que sólo gastan
// CPU. Tres por hora es de sobra para trabajar y no alcanza para vaciar la
// cuenta si el chat entra en un bucle.
const MAX_POR_HORA = 3;

const json = (b: unknown, s = 200) =>
  new Response(JSON.stringify(b), {
    status: s,
    headers: { ...CORS, "Content-Type": "application/json" },
  });

/** ¿Es una URL de imagen que el worker va a poder bajar?
 *
 *  Se valida acá y no en el worker porque acá el error todavía le puede llegar
 *  a una persona que puede arreglarlo. Cuatro minutos después, cuando el worker
 *  descubra que la foto no existe, ya se gastaron los créditos.
 */
function fotoValida(u: string): boolean {
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
    const id = new URL(req.url).searchParams.get("id");
    if (!id) return json({ error: "falta id" }, 400);

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
    return json({
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
    });
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

  if (mensaje.length < 10) {
    return json({ error: "el pedido está vacío", codigo: "pedido_incompleto" }, 400);
  }
  if (!foto) {
    return json({
      error: "un reel se arma A PARTIR de una foto de producto: sin foto no hay reel",
      codigo: "falta_la_foto",
    }, 400);
  }
  if (!fotoValida(foto)) {
    return json({
      error: "la foto tiene que ser una URL https pública que se pueda descargar",
      codigo: "foto_invalida",
    }, 400);
  }

  const desde = new Date(Date.now() - 3600_000).toISOString();
  const rc = await fetch(
    `${tabla}?creado_en=gte.${desde}&estado=not.in.(rechazado,error)&select=id`,
    { headers: { ...cab, Prefer: "count=exact" } },
  );
  const recientes = (await rc.json()) as unknown[];
  if (Array.isArray(recientes) && recientes.length >= MAX_POR_HORA) {
    return json({
      error: `ya se pidieron ${recientes.length} reels en la última hora, que es el ` +
        `tope. Cada uno cuesta créditos: si de verdad hacen falta más, hay que ` +
        `subir el tope a propósito.`,
      codigo: "tope_por_hora",
    }, 429);
  }

  const fila: Record<string, unknown> = { mensaje, foto, quien: c.quien ?? "Asistime" };
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
    demora_estimada_seg: 300,
  }, 201);
});
