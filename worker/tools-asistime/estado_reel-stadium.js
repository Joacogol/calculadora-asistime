// ════════════════════════════════════════════════════════════════════
//  estado_reel — cómo va el pedido
// ════════════════════════════════════════════════════════════════════
//
//  Atiende TRES pedidos que en el chat se parecen y no se parecen en nada
//  más. Decir lo de uno sobre otro manda a la persona a preocuparse por lo
//  que no es:
//
//    · `crear_video` → una IA genera el ARCHIVO. Sin título ni música: es
//                      material para editar después.
//    · `crear_reel`  → una IA genera la PIEZA terminada. Tarda unos cinco
//                      minutos, gasta plata y puede deformar el producto.
//    · `montar_reel` → se editan los videos que mandaron. Menos de dos
//                      minutos, no gasta nada, no hay nada inventado. Si un
//                      subtítulo salió mal se CORRIGE, no se rehace.
//
//  Decirle a alguien «miralo, la IA a veces deforma el producto» sobre un
//  video que filmó él mismo lo manda a buscar un problema que no existe. La
//  respuesta trae `pieza` y `montado`, así que se sabe cuál es cuál.
//
//  **La espera vive del otro lado, no acá.** El sandbox de las tools no sabe
//  dormir: un `setTimeout` no lo suspende, lo mata. Quien espera es la Edge
//  Function, que se queda hasta un minuto mirando la fila antes de contestar.

const API = "https://heajbidxysjxxegqemka.supabase.co/functions/v1/api-reels";
const CLAVE = "ea9aa1075970e01b40da429f393981443a831c4a606a0fe7c9cb1a66855238d7";

/** El texto del motor, cerrado con punto. Sus notas vienen sin puntuación
 *  final, y pegadas a la frase siguiente quedaban «no se pudo bajar
 *  Contáselos», que se lee como un error de la herramienta. */
function cerrado(t) {
  const s = String(t || "").trim();
  return !s ? "" : (/[.!?…]$/.test(s) ? s : s + ".");
}

const id = String(input.id || "").trim();
if (!id) {
  return { success: false, statusCode: 400, code: "falta_id",
           message: "Necesito el id que devolvió `crear_video`, `crear_reel`, " +
                    "`montar_reel` o `retocar_reel`." };
}

let r;
try {
  r = await fetch(API + "?id=" + encodeURIComponent(id), { headers: { "x-api-clave": CLAVE } });
} catch (e) {
  return { success: false, statusCode: 502, code: "sin_conexion",
           message: "No pude consultar cómo va. NO digas que falló ni que se " +
                    "gastó nada: no lo sabemos. Volvé a intentar." };
}
if (r.status === 404) {
  return { success: false, statusCode: 404, code: "no_existe",
           message: "No existe ningún pedido con ese id." };
}
if (!r.ok) {
  return { success: false, statusCode: r.status,
           code: r.status === 401 ? "clave_invalida" : "error_estudio",
           message: "No pude consultar cómo va el pedido." };
}

let d = {};
try { d = await r.json(); } catch (e) {
  return { success: false, statusCode: 502, code: "respuesta_rara",
           message: "El estudio contestó algo que no pude leer." };
}

// De qué camino salió y qué se pidió. Cambia todo lo que hay que decir.
const montado = d.montado === true;
const soloVideo = d.pieza === "video";
const que = soloVideo ? "video" : "reel";

// `rechazado` NO es un error: es el freno de gasto haciendo su trabajo. Se
// cuenta distinto de un fallo porque la respuesta del cliente es distinta —
// acá hay algo que decidir, no algo que reintentar. Sólo pasa con lo que
// genera una IA: montar no gasta créditos, así que no hay tope que pisar.
if (d.estado === "rechazado") {
  return { success: false, statusCode: 402, code: "tope_de_creditos",
           message: "No se generó porque supera el tope de gasto configurado. " +
                    cerrado(d.mensaje) + " Contáselos así: no falló nada y NO " +
                    "se gastó nada, hay un límite puesto a propósito y para " +
                    "pasarlo alguien lo tiene que subir." };
}

if (d.estado === "error") {
  return { success: false, statusCode: 500, code: "reel_fallido",
           message: cerrado(d.mensaje || "No se pudo hacer.") +
                    " Contáselos tal cual, sin inventarles otra razón. " +
                    (montado
                      ? "Montar no gasta créditos, así que volver a intentarlo " +
                        "no cuesta nada: si el motivo se puede arreglar —material " +
                        "muy largo, un pedido que no se podía cumplir— ofrecelo."
                      : "Ojo: es probable que ya se haya cobrado, así que NO lo " +
                        "vuelvas a pedir automáticamente — preguntá si quieren " +
                        "reintentarlo.") };
}

if (!d.listo) {
  const seg = d.esperando_seg || 0;
  // Un montaje que lleva ocho minutos está colgado; uno generado por IA recién
  // a los quince empieza a ser raro. El mismo número para los dos haría que uno
  // de los dos avisos llegue siempre tarde o siempre de más.
  const demorado = seg > (montado ? 480 : 900);
  return {
    success: true, listo: false, id: id, estado: d.estado,
    esperando_seg: seg, montado: montado, pieza: d.pieza || "reel",
    message: demorado
      ? "Lleva " + Math.round(seg / 60) + " minutos, mucho más de lo normal. " +
        "Deciles que hubo una demora y que lo estamos revisando."
      : (montado
          ? "Todavía no está (van " + seg + " segundos). **Esto NO es un error**: " +
            "volvé a llamar a `estado_reel` con el mismo id, ahora mismo. Un reel " +
            "montado con los videos que mandaron suele estar en menos de dos " +
            "minutos, o sea una o dos consultas."
          : "El " + que + " sigue generándose (van " + seg + " segundos de los " +
            "«unos cinco minutos» que tarda). Esto NO es un error, es lo " +
            "esperable. Volvé a llamar a `estado_reel` con el mismo id, ahora " +
            "mismo — la consulta espera un minuto adentro, así que van a hacer " +
            "falta unas cinco llamadas en total y está bien que sea así.") +
        " NO inventes el link ni describas cómo quedó.",
  };
}

// ── Se pidió el VIDEO: lo que hay es un archivo ──────────────────────────
//
// Y lo importante que sigue: ese archivo se puede usar. Es una URL pública,
// así que `montar_reel` lo toma como un clip más —con el título que la persona
// quiera, mezclado con material filmado, o cortado— sin volver a pagar la
// generación.
if (soloVideo) {
  return {
    success: true, listo: true, id: id, pieza: "video",
    video: d.video_crudo, proveedor: d.proveedor || null,
    notas: d.mensaje || null,
    message:
      "El video está listo. Pasales el link TAL CUAL viene, sin acortarlo: " +
      d.video_crudo + ". Es el archivo crudo: no tiene título ni música encima, " +
      "que es lo que se pidió.\n" +
      (d.mensaje ? "El motor dejó anotado esto, contáselo: " + cerrado(d.mensaje) + "\n" : "") +
      "Deciles que lo MIREN ENTERO antes de usarlo — lo genera una IA y en los " +
      "planos de movimiento a veces deforma el producto, las caras y las manos. " +
      "Si les sirve y ahora quieren la pieza para publicar, NO hay que generarlo " +
      "de nuevo ni volver a pagarlo: llamá a `montar_reel` con este mismo link " +
      "en `clips` y el título que quieran. Si el video no les gustó, pedirlo de " +
      "nuevo sí vuelve a costar — avisáselos antes.",
  };
}

return {
  success: true, listo: true, id: id, video: d.url, montado: montado,
  pieza: "reel", video_crudo: d.video_crudo || null,
  titulo: d.titulo || null, notas: d.mensaje || null,
  message:
    "El reel está listo. Pasales el link TAL CUAL viene, sin acortarlo: " + d.url +
    ". Es un MP4 vertical de 1080×1920 listo para subir a Instagram.\n" +
    (d.mensaje ? "El motor dejó anotado esto, contáselo antes de que lo suban: " +
      cerrado(d.mensaje) + "\n" : "") +
    (montado
      ? "Se armó con los videos que mandaron, así que no hay nada inventado y " +
        "no se gastaron créditos. Si algún subtítulo quedó mal, NO lo rehagas " +
        "con `montar_reel` —vuelve a escuchar el mismo audio y se equivoca " +
        "igual—: mirá las frases con `ver_reel` y corregi con `retocar_reel`."
      : "Lo generó una IA a partir de la foto: deciles que lo MIREN ENTERO " +
        "antes de publicar, porque a veces deforma el producto en los planos " +
        "de movimiento. " +
        (d.video_crudo
          ? "Si les gusta el video pero no el título o la música, NO hay que " +
            "volver a generarlo ni a pagarlo: quedó guardado aparte el archivo " +
            "sin nada encima (`video_crudo`) y `montar_reel` lo vuelve a armar " +
            "con otro texto, gratis. "
          : "") +
        "Si lo que no funciona es el video mismo, se puede volver a pedir con " +
        "el pedido corregido — avisales que ese intento sí gasta."),
};
