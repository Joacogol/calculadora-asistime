// ═══════════════════════════════════════════════════════════════════════
//  ver_reel — mostrar lo que el motor escribió, para poder corregirlo
// ═══════════════════════════════════════════════════════════════════════
//
//  Un reel sale con subtítulos que el sistema sacó del audio. Casi siempre
//  están bien; a veces una frase sale mal, y sobre todo los nombres propios.
//  Para corregir hace falta poder MIRAR, y con números: nadie puede decir
//  «esa frase» en un chat.
//
//  Las frases y los tramos vienen numerados desde 1. Esos son los números
//  que después usa `retocar_reel`.

const API = "https://ndulchsiqutxibiwzzlc.supabase.co/functions/v1/api-reels";
const CLAVE = "705fdf8433d7cb33ffaba7e95333c664bf8fd904bbea4fc5c211cf52f01a7e94";

const cab = { "Content-Type": "application/json", "x-api-clave": CLAVE };

// ── Qué palabras aprendió la marca ───────────────────────────────────────
if (input.correcciones === true) {
  let r;
  try {
    r = await fetch(API + "?correcciones=1", { headers: cab });
  } catch (e) {
    return { success: false, statusCode: 502, code: "sin_conexion",
      message: "No pude consultar la memoria de la marca. Probá de nuevo en un rato." };
  }
  const d = await r.json().catch(() => ({}));
  const lista = d.correcciones || [];
  return {
    success: true,
    correcciones: lista,
    message: lista.length
      ? "Estas son las palabras que la marca ya aprendió a escribir bien. " +
        "Mostráselas a la persona como una lista de «donde diga X, escribo Y», " +
        "y aclarale que puede pedir que olvide cualquiera."
      : "La marca todavía no aprendió ninguna corrección. Se aprenden solas " +
        "cuando alguien corrige una palabra en un reel.",
  };
}

const id = String(input.id || "").trim();
if (!id) {
  return { success: false, statusCode: 400, code: "falta_id",
    message: "Necesito el id del reel. Es el que te devolvió `montar_reel` o " +
             "`retocar_reel`. Si no lo tenés, preguntale a la persona de cuál " +
             "de los reels está hablando." };
}

let r;
try {
  r = await fetch(API + "?id=" + encodeURIComponent(id) + "&ver=1", { headers: cab });
} catch (e) {
  return { success: false, statusCode: 502, code: "sin_conexion",
    message: "No pude consultar el reel. Probá de nuevo en un rato." };
}

const d = await r.json().catch(() => ({}));
if (!r.ok) {
  return { success: false, statusCode: r.status, code: d.codigo || "no_pude_ver",
    message: (d.error || "No pude ver ese reel.") +
      (d.codigo === "sin_armado"
        ? " Decíselo a la persona con estas palabras, sin inventarle otra razón."
        : "") };
}

const frases = d.subtitulos || [];
const tramos = d.tramos || [];

return {
  success: true,
  id: d.id,
  url: d.url,
  hook: d.hook,
  cierre: d.cierre,
  subtitulos: frases,
  tramos: tramos,
  message:
    "Este reel tiene " + frases.length + " frases y " + tramos.length + " tramos. " +
    "Mostrale a la persona las frases NUMERADAS, una por renglón, tal cual " +
    "están escritas — no las arregles vos al mostrarlas, porque lo que tiene " +
    "que ver es lo que se ve en el video. Decile también cuál es el hook. " +
    "Después, si te marca algo mal, usá `retocar_reel`: por número de frase " +
    "si te dice cuál, o con `reemplazar` si te dice una palabra que está mal " +
    "escrita en varios lados.",
};
