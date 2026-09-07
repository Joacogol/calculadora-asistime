// La puerta de entrada para EDITAR UNA FOTO desde el chat de Asistime.
//
// Hermana de `api-disenos` y `api-reels`, y por las mismas razones: la tool no
// tiene dónde guardar secretos, así que lo que queda expuesto en su código es
// una clave que sólo sirve para encargar trabajo en UNA base. Si se filtra, lo
// peor que pasa es que alguien encargue ediciones —que gastan unos créditos y
// quedan registradas—, no que lea datos ni borre nada.
//
// ── Los seis verbos ──────────────────────────────────────────────────────
//
//   crear     inventa una foto nueva a partir de una descripción, sin partir
//             de ninguna: es el único que no lleva `foto`
//   fondo     recorta el producto y deja el fondo transparente
//   formato   estira la foto a otra proporción inventando los bordes
//   tamano    agranda una foto chica
//   retoque   saca o cambia algo puntual («sacale el cartel de oferta»)
//   escena    pone el producto en otro lugar («en una calle de noche»)
//
// `POST` anota el pedido y devuelve el id al instante. `GET` cuenta cómo va, y
// espera un rato adentro antes de contestar: una edición tarda segundos, así
// que la mayoría de las veces el agente puede mostrar la foto en el MISMO
// mensaje en vez de decir «ya te la mando».

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-api-clave",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
};

// Editar una foto sale unos pocos créditos —quitar el fondo son 3— así que el
// tope por hora es alto: acá no está la plata, está en los reels. Lo que este
// número frena es un bucle del chat, no el gasto.
const MAX_POR_HORA = Number(Deno.env.get("FOTOS_POR_HORA") ?? 40);

// Cuánto espera el GET a que la foto esté antes de contestar «todavía no».
// Las tools de Stadium tienen entre 60 y 120 segundos de timeout, así que 45
// entra cómodo y deja margen para lo que tarde el resto del turno.
const ESPERA_MAX_MS = 45_000;
const ESPERA_PASO_MS = 3_000;

const VERBOS = ["crear", "fondo", "formato", "tamano", "retoque", "escena"];
const FORMATOS = ["post", "vert", "story", "reel"];

// Los verbos que generan imagen a partir de una instrucción. Sin texto no hay
// nada que pedirle al modelo, y conviene decirlo ACÁ —donde el error todavía
// le llega a una persona que puede arreglarlo— y no en el worker.
const CON_INSTRUCCION = ["crear", "retoque", "escena"];

// El único que NO parte de una foto. Se escribe como lista y no como
// `verbo === "crear"` porque el día que haya otro generador desde cero, el
// que lo agregue va a encontrar acá el lugar donde decirlo.
const SIN_FOTO = ["crear"];

const json = (b: unknown, s = 200) =>
  new Response(JSON.stringify(b), {
    status: s,
    headers: { ...CORS, "Content-Type": "application/json" },
  });

/** ¿Es una URL de imagen que el worker va a poder bajar?
 *
 *  Se valida acá y no en el worker por lo mismo de siempre: acá el error
 *  todavía le puede llegar a alguien que puede corregirlo.
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

const dormir = (ms: number) => new Promise((r) => setTimeout(r, ms));


// ── Quién está llamando ──────────────────────────────────────────────────
//
// Hasta el 7/9/2026 esto era una comparación contra `API_CLAVE`: la función
// vivía en el proyecto de UN cliente, así que saber que la clave era la buena
// alcanzaba para saber en qué base escribir. Con todos los clientes en el
// mismo Supabase eso ya no cierra: la clave además tiene que decir DE QUIÉN
// es, porque de eso dependen el esquema donde vive su base y el bucket donde
// van sus archivos.
//
// Por eso `identificar` devuelve un cliente, no un sí o un no. Y por eso la
// tabla guarda el SHA-256 de la clave y no la clave: si alguien llega a leer
// `public.claves_api` no se lleva las llaves de nadie. La comparación la hace
// Postgres sobre un hash completo, así que no hay tiempo que mirar para
// adivinar la original.
//
// El cliente de la casa —Asistime, que vive en `public`— sigue entrando por
// `API_CLAVE`: no depende de la base para autenticarse, y así una migración
// a medias nunca lo deja afuera.

type Quien = {
  marca: string;
  esquema: string;
  bucket: string;
  usuario: string | null;
};

/** Comparación de largo constante. Con `===` el tiempo de respuesta varía
 *  según cuántos caracteres coinciden, y eso alcanza para adivinar la clave a
 *  fuerza de intentos. */
function misma_clave(dada: string, esperada: string): boolean {
  if (dada.length !== esperada.length) return false;
  let distinto = 0;
  for (let i = 0; i < esperada.length; i++) {
    distinto |= dada.charCodeAt(i) ^ esperada.charCodeAt(i);
  }
  return distinto === 0;
}

async function huella(texto: string): Promise<string> {
  const bytes = await crypto.subtle.digest(
    "SHA-256", new TextEncoder().encode(texto));
  return Array.from(new Uint8Array(bytes))
    .map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function identificar(
  dada: string, base: string, llave: string,
): Promise<Quien | null> {
  if (!dada) return null;

  const propia = Deno.env.get("API_CLAVE") || "";
  if (propia && misma_clave(dada, propia)) {
    return {
      marca: Deno.env.get("MARCA") || "",
      esquema: Deno.env.get("ESQUEMA") || "",
      bucket: Deno.env.get("BUCKET") || "disenos",
      usuario: Deno.env.get("USUARIO_ID") || null,
    };
  }

  const r = await fetch(
    `${base}/rest/v1/claves_resueltas?clave_sha=eq.${await huella(dada)}` +
    `&activa=is.true&select=marca,esquema,bucket,usuario_id&limit=1`,
    { headers: { apikey: llave, Authorization: `Bearer ${llave}` } },
  );
  if (!r.ok) return null;
  let filas: unknown;
  try { filas = await r.json(); } catch { return null; }
  if (!Array.isArray(filas) || !filas.length) return null;
  const f = filas[0] as Record<string, string | null>;
  return {
    marca: f.marca || "",
    esquema: f.esquema || "",
    bucket: f.bucket || "disenos",
    usuario: f.usuario_id || null,
  };
}

/** Las cabeceras con las que se habla con PostgREST. `Accept-Profile` elige el
 *  esquema al leer y `Content-Profile` al escribir; sin ellas se habla con
 *  `public`, que es lo que corresponde para quien tiene proyecto propio. */
function cabeceras(llave: string, esquema: string): Record<string, string> {
  const cab: Record<string, string> = {
    apikey: llave,
    Authorization: `Bearer ${llave}`,
    "Content-Type": "application/json",
  };
  if (esquema) {
    cab["Accept-Profile"] = esquema;
    cab["Content-Profile"] = esquema;
  }
  return cab;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

  const base = Deno.env.get("SUPABASE_URL")!;
  const llave = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

  const quien = await identificar(
    req.headers.get("x-api-clave") || "", base, llave);
  if (!quien) return json({ error: "clave inválida", codigo: "clave_invalida" }, 401);
  const { esquema, bucket, usuario } = quien;
  const cab = cabeceras(llave, esquema);
  const tabla = `${base}/rest/v1/fotos_editadas`;

  const leer = async (id: string) => {
    const r = await fetch(
      `${tabla}?id=eq.${encodeURIComponent(id)}&select=id,estado,url,notas,` +
        `verbo,creditos_estimados,creado_en`,
      { headers: cab },
    );
    const filas = await r.json();
    return Array.isArray(filas) && filas.length ? filas[0] : null;
  };

  const contestar = (f: Record<string, unknown>) => {
    const estado = String(f.estado);
    const terminado = ["listo", "error", "rechazado"].includes(estado);
    return {
      id: f.id,
      estado,
      listo: estado === "listo",
      terminado,
      url: f.url || null,
      verbo: f.verbo,
      creditos: f.creditos_estimados || null,
      mensaje: f.notas || null,
      esperando_seg: Math.round(
        (Date.now() - new Date(String(f.creado_en)).getTime()) / 1000,
      ),
    };
  };

  // ── Cómo va un pedido ──────────────────────────────────────────────────
  //
  // Espera adentro hasta que esté, en vez de contestar «todavía no» al
  // instante. Una edición tarda segundos: si el agente pregunta y se le dice
  // que espere, la persona se queda mirando un chat mudo por algo que ya
  // estaba listo dos segundos después.
  if (req.method === "GET") {
    const url0 = new URL(req.url);
    const id = url0.searchParams.get("id");
    if (!id) return json({ error: "falta id" }, 400);
    const esperar = url0.searchParams.get("esperar") !== "no";

    const hasta = Date.now() + (esperar ? ESPERA_MAX_MS : 0);
    for (;;) {
      const f = await leer(id);
      if (!f) return json({ error: "no existe", codigo: "no_existe" }, 404);
      const r = contestar(f);
      if (r.terminado || Date.now() >= hasta) return json(r);
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

  const verbo = String(c.verbo ?? "").trim().toLowerCase();
  const foto = String(c.foto ?? "").trim();
  const instruccion = String(c.instruccion ?? "").trim();
  const formato = String(c.formato ?? "").trim().toLowerCase();

  if (!VERBOS.includes(verbo)) {
    return json({
      error: `«${verbo || "(vacío)"}» no es algo que sepa hacer. Puedo: ` +
        `crear (inventar una foto desde una descripción, sin partir de otra), ` +
        `fondo (recortar el producto), formato (llevarla a otra proporción), ` +
        `tamano (agrandarla), retoque (sacar o cambiar algo puntual) y ` +
        `escena (poner el producto en otro lugar).`,
      codigo: "verbo_desconocido",
    }, 400);
  }
  if (!foto && !SIN_FOTO.includes(verbo)) {
    return json({
      error: "hay que decir qué foto editar: una URL https pública",
      codigo: "falta_la_foto",
    }, 400);
  }
  if (foto && !fotoValida(foto)) {
    return json({
      error: "la foto tiene que ser una URL https pública que se pueda descargar",
      codigo: "foto_invalida",
    }, 400);
  }
  if (CON_INSTRUCCION.includes(verbo) && instruccion.length < 4) {
    return json({
      error: `«${verbo}» necesita que le digas qué hacer. Por ejemplo: ` +
        (verbo === "crear"
          ? "«una sala de espera luminosa, sillas vacías, luz de mañana»."
          : verbo === "retoque"
          ? "«sacale el cartel de oferta que tiene abajo»."
          : "«poné la zapatilla en una vereda al atardecer»."),
      codigo: "falta_la_instruccion",
    }, 400);
  }
  if (verbo === "formato" && !FORMATOS.includes(formato)) {
    return json({
      error: `«formato» necesita a cuál: ${FORMATOS.join(", ")}.`,
      codigo: "falta_el_formato",
    }, 400);
  }
  // Para `crear` el formato es opcional —sin él sale cuadrada— pero uno mal
  // escrito se ignoraría en silencio y la foto saldría con otra proporción sin
  // que nadie entienda por qué. Mejor decirlo.
  if (formato && !FORMATOS.includes(formato)) {
    return json({
      error: `«${formato}» no es un formato. Son: ${FORMATOS.join(", ")}.`,
      codigo: "formato_desconocido",
    }, 400);
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
      error: `ya se pidieron ${recientes.length} ediciones en la última hora, ` +
        `que es el tope (variable FOTOS_POR_HORA).`,
      codigo: "tope_por_hora",
    }, 429);
  }

  const fila: Record<string, unknown> = {
    verbo, quien: c.quien ?? "Asistime",
  };
  // `crear` no tiene foto de entrada. Se omite la columna en vez de mandar ""
  // para que en la base se distinga «no lleva» de «venía vacía».
  if (foto) fila.foto = foto;
  if (instruccion) fila.instruccion = instruccion;
  if (formato) fila.formato = formato;
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
    demora_estimada_seg: 40,
  }, 201);
});
