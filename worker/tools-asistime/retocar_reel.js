// ═══════════════════════════════════════════════════════════════════════
//  retocar_reel — corregir un reel que ya salió, sin rehacerlo
// ═══════════════════════════════════════════════════════════════════════
//
//  Esto NO vuelve a escuchar el audio, y ese es todo el punto: si lo hiciera,
//  volvería a entender mal exactamente las mismas palabras (el modelo es
//  determinista con el mismo audio) y de paso tiraría las veinte frases que
//  estaban bien. Reusa lo que el motor ya armó y le cambia lo que se le pida.
//
//  Tampoco pisa el reel anterior: sale uno nuevo. Si la corrección quedó peor,
//  el original sigue estando.
//
//  Las mismas dos reglas de sandbox que `ver_reel`, por el mismo motivo:
//  leer el cuerpo con `try { await r.json() }` y nunca devolver `null`. Y
//  todo adentro de un `try`, para que una rotura se pueda leer en vez de
//  aparecer como «Error» a secas.
try {

const API = "https://ndulchsiqutxibiwzzlc.supabase.co/functions/v1/api-reels";
const CLAVE = "705fdf8433d7cb33ffaba7e95333c664bf8fd904bbea4fc5c211cf52f01a7e94";

const cab = { "Content-Type": "application/json", "x-api-clave": CLAVE };

// ── Olvidar una corrección aprendida ─────────────────────────────────────
const olvidar = String(input.olvidar || "").trim();
if (olvidar) {
  let r;
  try {
    r = await fetch(API, { method: "POST", headers: cab,
      body: JSON.stringify({ olvidar: olvidar }) });
  } catch (e) {
    return { success: false, statusCode: 502, code: "sin_conexion",
      message: "No pude llegar al motor. Probá de nuevo en un rato." };
  }
  let d = {};
  try { d = await r.json(); } catch (e) { d = {}; }
  return { success: r.ok, olvidadas: d.olvidadas || 0,
    message: d.nota || "No pude olvidar esa corrección." };
}

const id = String(input.reel || "").trim();
if (!id) {
  return { success: false, statusCode: 400, code: "falta_id",
    message: "Necesito el id del reel a corregir. Es el que devolvió " +
             "`montar_reel`. Si no lo tenés, preguntale a la persona de cuál " +
             "está hablando." };
}

// Los cambios se arman acá y no se le piden a la persona en este formato:
// ella dice «la cuarta está mal, tiene que decir tal cosa» y eso lo traducís
// vos. Nunca le muestres este JSON.
const cambios = {};
if (Array.isArray(input.reemplazar) && input.reemplazar.length) {
  cambios.reemplazar = input.reemplazar;
}
if (Array.isArray(input.subtitulos) && input.subtitulos.length) {
  cambios.subtitulos = input.subtitulos;
}
if (Array.isArray(input.quitar) && input.quitar.length) cambios.quitar = input.quitar;
if (Array.isArray(input.orden) && input.orden.length) cambios.orden = input.orden;
if (typeof input.hook === "string") cambios.hook = input.hook;
if (typeof input.cierre === "string") cambios.cierre = input.cierre;
if (input.recordar === false) cambios.recordar = false;

if (!Object.keys(cambios).length) {
  return { success: false, statusCode: 400, code: "sin_cambios",
    message: "No me dijiste qué corregir. Preguntale a la persona qué está " +
             "mal: si es una frase puntual, cuál y qué tiene que decir; si es " +
             "una palabra que sale mal escrita, cuál y cómo va." };
}

let r;
try {
  r = await fetch(API, { method: "POST", headers: cab,
    body: JSON.stringify({
      retocar: id,
      cambios: cambios,
      quien: input.quien || "Asistime",
      mensaje: input.mensaje || "",
    }) });
} catch (e) {
  return { success: false, statusCode: 502, code: "sin_conexion",
    message: "No pude llegar al motor. Decile a la persona que lo intente de " +
             "nuevo en unos minutos." };
}

let d = {};
try { d = await r.json(); } catch (e) { d = {}; }

if (!r.ok) {
  return { success: false, statusCode: r.status, code: d.codigo || "no_pude_retocar",
    message: (d.error || "El motor rechazó la corrección y no dijo por qué.") +
      " Decíselo a la persona con estas palabras, sin inventarle otra razón, y " +
      "si es un número fuera de rango, volvé a mirar con `ver_reel` antes de " +
      "insistir." };
}

return {
  success: true,
  id: d.id || "",
  origen: d.origen || "",
  aprendidas: d.aprendidas || 0,
  message:
    "Corrección tomada. Sale un reel NUEVO (id " + (d.id || "") + "); el " +
    "anterior queda como está, por si la corrección no gusta. Tarda un minuto " +
    "y medio más o menos: avisale a la persona que lo estás corrigiendo y " +
    "después consultá `estado_reel` con el id nuevo. NO llames a `montar_reel` " +
    "por esto — eso empezaría de cero y volvería a equivocarse igual." +
    (d.aprendidas
      ? " Además anoté la corrección para la marca, así que de acá en más esa " +
        "palabra sale bien sola en todos los reels: decíselo, que es la parte " +
        "que más le va a servir."
      : ""),
};

} catch (e) {
  return { success: false, statusCode: 500, code: "error_interno",
    message: "La herramienta se rompió por dentro: " +
             ((e && e.message) ? e.message : String(e)) +
             ". Contáselo tal cual a la persona: es un problema del sistema y " +
             "no de lo que pidió, y con ese texto se puede arreglar." };
}
