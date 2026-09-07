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
//
//  ── Dos reglas de este sandbox, aprendidas a los golpes ────────────────
//
//  El 1/9/2026 esta herramienta devolvió «Error» en el simulador, sin una
//  línea más. Los registros del otro lado mostraban que la API había
//  contestado 200: la respuesta llegó bien y algo se rompió DESPUÉS, ya
//  adentro del sandbox. El mismo código corre sin una queja fuera de acá.
//
//  1. **Sólo idiomas que ya se sabe que corren.** Las herramientas que
//     funcionan hace semanas leen el cuerpo con `try { await r.json() }`.
//     Ésta usaba `await r.json().catch(...)`, que es lo único que no
//     aparece en ninguna de las que andan. Se cambió por el idioma probado.
//     No es elegancia: es no estrenar construcciones en producción.
//  2. **Nada que salga de acá puede ser `null`.** Un reel sin placa de
//     cierre devolvía `cierre: null`, y este entorno no es el navegador.
//     Cuesta nada mandar `""`.
//
//  Y sobre todo: **todo va adentro de un `try`**. Una herramienta que muere
//  diciendo «Error» y nada más no se puede arreglar desde afuera — ni por la
//  persona que la usa, ni por quien la escribió. Si se rompe, que lo diga.
try {

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
  let d = {};
  try { d = await r.json(); } catch (e) { d = {}; }
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

let d = {};
try { d = await r.json(); } catch (e) { d = {}; }

if (!r.ok) {
  return { success: false, statusCode: r.status, code: d.codigo || "no_pude_ver",
    message: (d.error || "No pude ver ese reel.") +
      (d.codigo === "sin_armado"
        ? " Decíselo a la persona con estas palabras, sin inventarle otra razón."
        : "") };
}

const frases = d.subtitulos || [];
const tramos = d.tramos || [];

// La lista ya armada, en texto. Así el agente no tiene que rearmarla —y no
// puede equivocarse numerando— y la persona ve exactamente lo que se ve en
// el video.
let lista = "";
for (let i = 0; i < frases.length; i++) {
  lista += frases[i].n + ". " + frases[i].texto + "\n";
}

return {
  success: true,
  id: d.id || id,
  url: d.url || "",
  hook: d.hook || "",
  cierre: d.cierre || "",
  subtitulos: frases,
  tramos: tramos,
  message:
    "Este reel tiene " + frases.length + " frases y " + tramos.length + " tramos.\n" +
    (d.hook ? "El hook dice: «" + d.hook + "»\n" : "No tiene hook.\n") +
    "Las frases, tal cual salen en el video:\n" + lista +
    "Mostráselas así, numeradas y una por renglón, SIN arreglarlas vos: lo que " +
    "tiene que ver es lo que se ve en el video. Después, si te marca algo mal, " +
    "usá `retocar_reel`: por número de frase si te dice cuál, o con " +
    "`reemplazar` si te dice una palabra que está mal escrita en varios lados.",
};

} catch (e) {
  return { success: false, statusCode: 500, code: "error_interno",
    message: "La herramienta se rompió por dentro: " +
             ((e && e.message) ? e.message : String(e)) +
             ". Contáselo tal cual a la persona: es un problema del sistema y " +
             "no de lo que pidió, y con ese texto se puede arreglar." };
}
