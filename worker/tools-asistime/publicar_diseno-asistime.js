// ═══════════════════════════════════════════════════════════════════
//  publicar_diseno — manda al Instagram de @asistime.ai una pieza NUESTRA
// ═══════════════════════════════════════════════════════════════════
//
//  Publica una pieza que el sistema diseñó, nombrada por su `diseno_id`.
//  Nunca por una URL: lo que sale al feed es siempre un archivo que pasó por
//  acá. Para una foto o un video que mandaron en el chat está
//  `publicar_archivo`; para un reel del motor, `publicar_reel`.
//
//  ── Encolar no es publicar ─────────────────────────────────────────
//
//  Esto escribe una fila en una cola y el worker la sube en el próximo
//  minuto. Meta puede rechazar la pieza después, y eso recién se sabe cuando
//  el worker la sube. Por eso el mensaje de abajo insiste: hasta que
//  `estado_publicacion` no diga «publicado», no está publicado.
//
//  ── Un diseño con dos piezas no se publica solo ────────────────────
//
//  Una vertical no entra en el feed y una placa cuadrada no es una story: son
//  publicaciones distintas y las dos son razonables. Si el diseño tiene de las
//  dos, la API contesta `elegir_tipo` con las opciones y hay que preguntar.
//  Elegir por la persona sería adivinar cuál quería.

const API = "https://qxjvtxumkljsroukpkny.supabase.co/functions/v1/api-publicar";
const CLAVE = "26cfe17eee7b67d8292bcc52f1039ca105f03967c4a1667594b199c7d0b1700e";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const diseno_id = String(input.diseno_id || "").trim();
if (!UUID.test(diseno_id)) {
  return {
    success: false, statusCode: 400, code: "diseno_id_invalido",
    message:
      "«" + diseno_id + "» no es el id de un diseño. El id es un uuid y lo " +
      "devolvió `crear_diseno` — copialo tal cual de ahí, no lo inventes ni " +
      "uses el número de un mensaje.",
  };
}

const cuerpo = { diseno_id: diseno_id };
if (input.tipo) cuerpo.tipo = String(input.tipo).trim().toLowerCase();
if (input.caption) cuerpo.caption = String(input.caption);
if (input.publicar_en) cuerpo.publicar_en = String(input.publicar_en);

let r;
try {
  r = await fetch(API, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-api-clave": CLAVE },
    body: JSON.stringify(cuerpo),
  });
} catch (e) {
  return {
    success: false, statusCode: 502, code: "sin_conexion",
    message: "No pude comunicarme con el estudio. NO digas que se publicó: " +
             "no se encoló nada. Que lo intenten de nuevo en unos minutos.",
  };
}

let d = {};
try { d = await r.json(); } catch (e) { d = {}; }

// Falta elegir entre feed y story: no es un error, es una pregunta.
if (d.codigo === "elegir_tipo" || d.codigo === "tipo_no_disponible") {
  return {
    success: true,
    falta_elegir: "tipo",
    opciones: d.opciones || [],
    message:
      (d.error || "Hay que elegir qué se publica.") +
      " Preguntale cuál quiere y volvé a llamarme con `tipo`. NO elijas vos.",
  };
}

// Ya estaba publicado o en camino: mostrar lo que hay, no duplicar el posteo.
if (d.codigo === "ya_publicado") {
  return {
    success: true,
    ya_estaba: true,
    publicaciones: d.publicaciones || [],
    message:
      "Este diseño ya se había mandado a publicar, así que no se encoló de " +
      "nuevo. Contale en qué estado está y, si hay `permalink`, pasáselo.",
  };
}

if (!r.ok) {
  const ayuda = {
    sin_instagram:
      "No hay una cuenta de Instagram conectada y activa. Se conecta desde la " +
      "app; si el token venció, hay que renovarlo. NO se publicó nada.",
    no_esta_listo:
      "El diseño todavía no está terminado. Consultá `estado_diseno` y volvé " +
      "cuando esté listo.",
    sin_piezas:
      "Este diseño no tiene ninguna pieza que Instagram acepte.",
  };
  return {
    success: false, statusCode: r.status,
    code: d.codigo || (r.status === 429 ? "tope_por_hora" : "error_estudio"),
    message: ayuda[d.codigo] || d.error ||
             "No se pudo encolar la publicación y no sé por qué.",
  };
}

return {
  success: true,
  diseno_id: d.diseno_id,
  tipo: d.tipo,
  cuenta: d.cuenta,
  cuando: d.cuando,
  publicaciones: d.publicaciones,
  message:
    "Encolado para " + (d.cuenta ? "@" + d.cuenta : "la cuenta conectada") +
    " como " + d.tipo + ", " + d.cuando + ". **Todavía no está publicado.** " +
    "Consultá `estado_publicacion` con el diseno_id " + d.diseno_id +
    " —esa consulta espera adentro, así que lo más probable es que puedas " +
    "confirmarlo en el mismo mensaje— y recién cuando diga «publicado» decí " +
    "que salió, y pasá el link. NO vuelvas a llamar a publicar_diseno por " +
    "este mismo diseño: publicaría dos veces.",
};
