// ═══════════════════════════════════════════════════════════════════
//  publicar_archivo — sube tal cual una foto o un video que mandaron
// ═══════════════════════════════════════════════════════════════════
//
//  Para lo que ya está listo y no hay que diseñar: la foto de una pantalla,
//  el video que grabó alguien del equipo. Si la pieza la dibujó el sistema,
//  va `publicar_diseno`; si es un reel del motor, `publicar_reel`. Dos
//  puertas para el mismo trabajo es lo que hace que un agente elija mal, así
//  que estas tres no se pisan.
//
//  El archivo se BAJA, se verifica por sus bytes que sea imagen o video de
//  verdad, se le sacan los metadatos —dónde y con qué se sacó la foto— y se
//  guarda en nuestro Storage. Lo que sale a Instagram es siempre nuestra
//  copia, nunca la URL que le dictaron al agente.
//
//  ── Por qué acá sí hace falta `confirmado` ─────────────────────────
//
//  Las otras dos publican algo que el sistema hizo y que la persona ya vio en
//  el chat. Esto publica un archivo que llegó suelto: la única mirada humana
//  posible es la de quien lo mandó, y «subilo» dicho al pasar no es lo mismo
//  que «sí, publicalo en la cuenta». Es la cuenta de la empresa y no se
//  deshace.

const API = "https://qxjvtxumkljsroukpkny.supabase.co/functions/v1/api-publicar/foto";
const CLAVE = "26cfe17eee7b67d8292bcc52f1039ca105f03967c4a1667594b199c7d0b1700e";

const archivo = String(input.archivo || "").trim();
if (!archivo) {
  return {
    success: false, statusCode: 400, code: "falta_el_archivo",
    message: "Necesito la URL del archivo que mandaron, copiada tal cual del " +
             "chat y sin acortar.",
  };
}
if (!/^https?:\/\//i.test(archivo)) {
  return {
    success: false, statusCode: 400, code: "archivo_invalido",
    message: "Eso no es una URL que se pueda bajar. Copiá la del chat, entera.",
  };
}

if (input.confirmado !== true) {
  return {
    success: false, statusCode: 400, code: "falta_confirmar",
    message:
      "Antes de subir algo a la cuenta de Instagram de Asistime hace falta " +
      "que la persona lo confirme. Mostrale qué vas a publicar —el archivo y " +
      "el texto que lleva— y preguntale si lo publicás. Con un «sí» claro, " +
      "volvé a llamarme con `confirmado: true`. Publicar no se deshace.",
  };
}

const cuerpo = { archivo: archivo };
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

if (d.codigo === "elegir_tipo" || d.codigo === "tipo_no_disponible") {
  return {
    success: true, falta_elegir: "tipo", opciones: d.opciones || [],
    message: (d.error || "Hay que elegir qué se publica.") +
             " Preguntale cuál quiere y volvé a llamarme con `tipo`.",
  };
}

if (!r.ok) {
  const ayuda = {
    sin_instagram:
      "No hay una cuenta de Instagram conectada y activa. Se conecta desde la " +
      "app; si el token venció, hay que renovarlo. NO se publicó nada.",
    foto_no_sirve:
      "El archivo no se pudo bajar o no es una imagen ni un video de los que " +
      "Instagram acepta (fotos en JPG o PNG, videos en MP4 o MOV). Pedile que " +
      "lo mande de nuevo.",
    video_muy_pesado:
      "El video pesa más de lo que esta puerta puede mover. Que lo suban a " +
      "mano, o que manden uno más corto.",
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
  message:
    "Encolado para " + (d.cuenta ? "@" + d.cuenta : "la cuenta conectada") +
    " como " + d.tipo + ", " + d.cuando + ". **Todavía no está publicado.** " +
    "Consultá `estado_publicacion` con el diseno_id " + d.diseno_id + " y " +
    "recién cuando diga «publicado» decí que salió y pasá el link.",
};
