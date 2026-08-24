// La puerta para pedir una PLANTILLA nueva desde afuera de la app.
//
// Hermana de `api-disenos`, y a propósito casi idéntica: encargar, consultar,
// confirmar. Lo que cambia es el objeto — ahí se pide una pieza, acá se pide la
// plantilla con la que después se hacen muchas piezas.
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

function json(cuerpo: unknown, status = 200) {
  return new Response(JSON.stringify(cuerpo), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
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

  // ── Cómo va un pedido ──────────────────────────────────────────────────
  if (req.method === "GET") {
    const id = url.searchParams.get("id");
    if (!id) return json({ error: "falta el id" }, 400);

    const r = await fetch(
      `${base}/rest/v1/plantilla_pedidos?id=eq.${encodeURIComponent(id)}` +
      `&select=id,estado,plantilla,version,preview,notas,mensaje_agente,creado_en`,
      { headers: cab });
    if (!r.ok) return json({ error: "no pude consultar el pedido" }, 500);

    const filas = await r.json();
    if (!filas.length) return json({ error: "no existe ese pedido" }, 404);
    const p = filas[0];

    const terminado = p.estado === "listo" || p.estado === "error";
    const esperando = Math.round(
      (Date.now() - new Date(p.creado_en).getTime()) / 1000);

    // Si terminó, se devuelve además el contrato: el agente necesita saber qué
    // campos tiene la plantilla nueva para poder usarla en la pieza siguiente
    // sin esperar a que el catálogo se regenere.
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
      preview: p.preview || [],
      campos,
      notas: p.notas,
      mensaje: p.mensaje_agente,
    });
  }

  // ── Pedir una plantilla nueva ──────────────────────────────────────────
  if (req.method === "POST") {
    let cuerpo: Record<string, unknown> = {};
    try { cuerpo = await req.json(); } catch { /* queda vacío */ }

    const mensaje = String(cuerpo.mensaje || "").trim();
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

    const r = await fetch(`${base}/rest/v1/plantilla_pedidos`, {
      method: "POST",
      headers: { ...cab, Prefer: "return=representation" },
      body: JSON.stringify({ mensaje, quien: cuerpo.quien || "Asistime" }),
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
      // Armar una plantilla lleva más que una pieza: se escribe, se renderiza,
      // se mira y se corrige. Decirlo acá evita que el chat prometa un minuto.
      demora_estimada_seg: 300,
    }, 201);
  }

  return json({ error: "método no soportado" }, 405);
});
