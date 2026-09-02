// ═══════════════════════════════════════════════════════════════════════
//  montar_reel — editar los videos que mandaron, no inventar uno
// ═══════════════════════════════════════════════════════════════════════
//
//  La hermana gratis de `crear_reel`. Ahí un modelo inventa el video y cuesta
//  miles de créditos; acá el material ya existe y lo único que se hace es
//  cortarlo, pegarlo y subtitularlo.
//
//  ── Lo nuevo del 2/9/2026: material largo ─────────────────────────
//
//  `instruccion` y `duracion` van en el guion. Con eso, y si el material es
//  más largo que el reel, el worker le da los videos a Gemini agéntico para
//  que elija los tramos (motor/mirar.py) y después el motor corta, encuadra
//  siguiendo a las caras (motor/encuadre.py), subtitula y arma. Si Gemini no
//  puede, el reel sale igual cortando por audio, y las notas lo dicen.
//
//  Es la tool 2189 del tenant 1 (Asistime). Stadium (2149) y Clínica (2153)
//  tienen la versión anterior, sin `instruccion` ni `duracion`: cuando se
//  lleve a los demás clientes, se copia ésta con su URL y su clave.

const API = "https://qxjvtxumkljsroukpkny.supabase.co/functions/v1/api-reels";
const CLAVE = "26cfe17eee7b67d8292bcc52f1039ca105f03967c4a1667594b199c7d0b1700e";

const clips = Array.isArray(input.clips) ? input.clips.map(String).filter(Boolean) : [];
if (!clips.length) {
  return { success: false, statusCode: 400, code: "faltan_los_clips",
    message: "No me pasaste ningún video. Copiá las URLs tal cual de la " +
             "conversación, enteras y sin acortarlas. Si todavía no mandaron " +
             "nada, pedíselos." };
}

const mensaje = String(input.mensaje || "").trim();
if (mensaje.length < 10) {
  return { success: false, statusCode: 400, code: "pedido_incompleto",
    message: "Escribí en una o dos frases qué reel es y qué pidieron. Sale de " +
             "lo que ya dijeron, no se lo preguntes." };
}

// El guion casi nunca trae tramos: vos no ves los videos. Lo que sí puede
// traer es la instrucción y el largo, que es lo que el sistema necesita para
// mirar el material y elegir por vos.
const guion = {};
if (typeof input.hook === "string" && input.hook.trim()) guion.hook = input.hook.trim();
if (typeof input.cierre === "string" && input.cierre.trim()) guion.cierre = input.cierre.trim();
if (typeof input.instruccion === "string" && input.instruccion.trim()) {
  guion.instruccion = input.instruccion.trim();
}
const dur = Number(input.duracion);
if (dur && dur >= 5 && dur <= 90) guion.duracion_objetivo = Math.round(dur);
guion.subtitulos = input.subtitulos === false ? [] : "auto";
guion.cortar_silencios = input.cortar_silencios !== false;

let r;
try {
  r = await fetch(API, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-api-clave": CLAVE },
    body: JSON.stringify({ mensaje: mensaje, clips: clips, guion: guion,
                           quien: input.quien || "Asistime" }),
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

const largo = !!guion.instruccion;
return {
  success: true, id: d.id, estado: d.estado, cuesta_creditos: false,
  message:
    "Reel tomado con " + clips.length + (clips.length === 1 ? " video" : " videos") +
    ". **No cuesta créditos.** " +
    (largo
      ? "Como el material es largo, el sistema lo va a MIRAR entero y elegir los " +
        "tramos según la instrucción: tarda unos minutos. "
      : "Suele estar en menos de dos minutos. ") +
    "Avisales que lo estás armando y después consultá `estado_reel` con el id " +
    d.id + ". NO describas cómo quedó antes de tenerlo. Y **guardá ese id**: es " +
    "lo que después deja corregirle los subtítulos con `ver_reel` y " +
    "`retocar_reel` sin tener que rehacerlo.",
};
