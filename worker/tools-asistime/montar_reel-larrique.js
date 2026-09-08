// ═══════════════════════════════════════════════════════════════════════
//  montar_reel (Larrique) — fotos de producto convertidas en video
// ═══════════════════════════════════════════════════════════════════════
//
//  Es la versión de Larrique de la tool 2189 de Asistime, y se guarda aparte
//  —contra la regla de este directorio de no duplicar— porque NO es la misma
//  con otra URL: acá el caso normal son FOTOS, no clips.
//
//  Larrique vende repuestos. No filma: fotografía. Manda dos o tres fotos de
//  un rulemán y quiere un video. El motor las dibuja con un acercamiento
//  lento (`motor/video._segmento_foto`), y esta tool lo único que agrega es
//  saber que un reel de fotos NO tiene audio: no hay nada que transcribir ni
//  ningún silencio que sacar, y pedirlo igual manda al worker a escuchar tres
//  imágenes.
//
//  **No gasta créditos, y por eso mismo no inventa nada.** Para un repuesto es
//  lo único aceptable: el manual de Larrique exige que la forma, la marca y el
//  empaque coincidan con el producto real, y ninguna IA acierta un rulemán NTN
//  con su caja. El camino caro (`crear_video`) es el equivocado acá, no sólo
//  el caro.
//
//  Es la tool 2258 del tenant 80. Su compañera es `estado_reel` (2259).

const API = "https://qxjvtxumkljsroukpkny.supabase.co/functions/v1/api-reels";
const CLAVE = "e48ac1d2d7b17611fba71e4450eae31fe326a267c5f7052b72000c484991f1a1";

const ES_FOTO = /\.(jpg|jpeg|png|webp|avif|heic)(\?|#|$)/i;

try {
  const material = Array.isArray(input.material)
    ? input.material.map(String).filter(Boolean)
    : (Array.isArray(input.clips) ? input.clips.map(String).filter(Boolean) : []);

  if (!material.length) {
    return { success: false, statusCode: 400, code: "falta_el_material",
      message: "No me pasaste ninguna foto ni ningún video. Copiá las URLs tal " +
               "cual de la conversación, enteras y sin acortarlas. Si todavía " +
               "no mandaron nada, pedíselo: con dos o tres fotos del producto " +
               "alcanza." };
  }

  const mensaje = String(input.mensaje || "").trim();
  if (mensaje.length < 10) {
    return { success: false, statusCode: 400, code: "pedido_incompleto",
      message: "Escribí en una o dos frases qué video es y qué pidieron. Sale " +
               "de lo que ya dijeron, no se lo preguntes." };
  }

  const fotos = material.filter(function (u) { return ES_FOTO.test(u); });
  const solo_fotos = fotos.length === material.length;

  const guion = {};
  if (typeof input.hook === "string" && input.hook.trim()) guion.hook = input.hook.trim();
  if (typeof input.cierre === "string" && input.cierre.trim()) guion.cierre = input.cierre.trim();
  if (typeof input.instruccion === "string" && input.instruccion.trim()) {
    guion.instruccion = input.instruccion.trim();
  }
  const dur = Number(input.duracion);
  if (dur && dur >= 5 && dur <= 90) guion.duracion_objetivo = Math.round(dur);

  // Un reel de fotos no tiene audio: no hay nada que transcribir ni ningún
  // silencio que sacar. Pedirlo igual no rompe nada pero manda al worker a
  // escuchar tres imágenes, que tarda y no devuelve una sola palabra.
  if (solo_fotos) {
    guion.subtitulos = [];
    guion.cortar_silencios = false;
  } else {
    guion.subtitulos = input.subtitulos === false ? [] : "auto";
    guion.cortar_silencios = input.cortar_silencios !== false;
  }

  let r;
  try {
    r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-clave": CLAVE },
      body: JSON.stringify({ mensaje: mensaje, clips: material, guion: guion,
                             quien: input.quien || "Larrique" }),
    });
  } catch (e) {
    return { success: false, statusCode: 502, code: "sin_conexion",
      message: "No pude comunicarme con el estudio. Que lo intenten de nuevo en " +
               "unos minutos. NO se gastó nada." };
  }

  let d = {};
  try { d = await r.json(); } catch (e) { d = {}; }

  if (!r.ok) {
    return { success: false, statusCode: r.status, code: d.codigo || "error_estudio",
      message: (d.error || "El estudio rechazó el pedido y no dijo por qué.") +
               " Decíselo a la persona con estas palabras, sin inventarle otra razón." };
  }

  const cuantas = material.length;
  return {
    success: true, id: d.id || "", estado: d.estado || "",
    cuesta_creditos: false, solo_fotos: solo_fotos,
    message:
      "Tomado con " + cuantas + (solo_fotos
        ? (cuantas === 1 ? " foto" : " fotos")
        : (cuantas === 1 ? " archivo" : " archivos")) +
      ". **No cuesta créditos.** " +
      (solo_fotos
        ? "Cada foto entra con un acercamiento lento y dura unos dos segundos y " +
          "medio, así que van a ser unos " + Math.round(cuantas * 2.5) + " segundos " +
          "más las placas. Suele estar en menos de dos minutos. "
        : "Suele estar en menos de dos minutos. ") +
      "Avisales que lo estás armando y después consultá `estado_reel` con el id " +
      (d.id || "") + ". NO describas cómo quedó antes de tenerlo, y **guardá ese " +
      "id**.",
  };
} catch (e) {
  return { success: false, statusCode: 500, code: "error_inesperado",
    message: "Se me rompió algo al armar el video: " + String(e && e.message || e) };
}
