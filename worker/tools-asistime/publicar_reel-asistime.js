// ═══════════════════════════════════════════════════════════════════
//  publicar_reel — sube al Instagram de @asistime.ai un reel del motor
// ═══════════════════════════════════════════════════════════════════
//
//  Un reel no vive en `disenos` sino en `reels`, así que `publicar_diseno` no
//  lo encuentra. Esta puerta lo toma por su `reel_id` y lo anota como un
//  diseño de una pieza, para que siga el mismo camino que todo lo demás.
//
//  El video NO se copia: ya está en nuestro bucket, lo subió el motor.
//
//  ── El id para consultar el estado es OTRO ─────────────────────────
//
//  Entra un `reel_id` y sale un `diseno_id`. `estado_publicacion` quiere el
//  segundo. Es el error más fácil de cometer acá.

const API = "https://qxjvtxumkljsroukpkny.supabase.co/functions/v1/api-publicar/reel";
const CLAVE = "26cfe17eee7b67d8292bcc52f1039ca105f03967c4a1667594b199c7d0b1700e";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const reel_id = String(input.reel_id || "").trim();
if (!UUID.test(reel_id)) {
  return {
    success: false, statusCode: 400, code: "reel_id_invalido",
    message:
      "«" + reel_id + "» no es el id de un reel. El id es un uuid y lo " +
      "devolvieron `crear_reel` o `montar_reel` — copialo tal cual.",
  };
}

const cuerpo = { reel_id: reel_id };
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
             "no se encoló nada.",
  };
}

let d = {};
try { d = await r.json(); } catch (e) { d = {}; }

// Un video se puede publicar como REEL —queda en la grilla— o como STORY,
// que se va en 24 horas. Son dos publicaciones distintas y las dos son
// razonables, así que la API pregunta en vez de elegir. Esta rama faltaba, y
// sin ella el agente recibía la pregunta como error y no tenía con qué
// contestarla.
if (d.codigo === "elegir_tipo" || d.codigo === "tipo_no_disponible") {
  return {
    success: true, falta_elegir: "tipo", opciones: d.opciones || [],
    message:
      (d.error || "Hay que elegir dónde va.") +
      " El reel queda en la grilla del perfil; la story se va en 24 horas. " +
      "Preguntale cuál quiere y volvé a llamarme con `tipo`. NO elijas vos.",
  };
}

if (d.codigo === "ya_publicado") {
  return {
    success: true, ya_estaba: true, publicaciones: d.publicaciones || [],
    message: "Este reel ya se había mandado a publicar, así que no se encoló " +
             "de nuevo. Contale en qué estado está y pasale el link si lo hay.",
  };
}

if (!r.ok) {
  const ayuda = {
    sin_instagram:
      "No hay una cuenta de Instagram conectada y activa. Se conecta desde la " +
      "app; si el token venció, hay que renovarlo. NO se publicó nada.",
    no_esta_listo:
      "El reel todavía se está armando. Consultá `estado_reel` y volvé cuando " +
      "esté listo.",
    no_existe: "No encuentro ese reel. Revisá el id.",
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
  reel_id: reel_id,
  cuenta: d.cuenta,
  cuando: d.cuando,
  message:
    "Reel encolado para " + (d.cuenta ? "@" + d.cuenta : "la cuenta conectada") +
    ", " + d.cuando + ". **Todavía no está publicado.** Consultá " +
    "`estado_publicacion` con el diseno_id " + d.diseno_id + " —OJO: ése, no " +
    "el reel_id— y recién cuando diga «publicado» decí que salió y pasá el " +
    "link. NO vuelvas a llamar por este mismo reel.",
};
