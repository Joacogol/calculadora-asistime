// estado_reel — ¿ya está?
//
// UNA sola consulta, sin bucle. La espera la hace `api-reels`, que se queda
// hasta 55 segundos adentro antes de contestar «todavía no».
//
// Sirve para TRES pedidos que no se cuentan igual, y decir lo de uno del otro
// manda a la persona a preocuparse por lo que no es:
//
//   · un VIDEO generado (`crear_video`) → un archivo, sin nada encima;
//   · un REEL generado (`crear_reel`)   → pieza terminada, hecha por una IA:
//                                         hay que mirarla por si deformó caras;
//   · un MONTAJE (`montar_reel`)        → material del club, nada inventado
//                                         adentro y ningún crédito gastado.
//
// La base lo distingue con `pieza` y `montado`.
//
// ** No pongas un bucle acá. ** El sandbox de las tools no sabe dormir: un
// `await new Promise(r => setTimeout(r, 10000))` no lo suspende, lo mata. Ver
// la nota larga en `estado_diseno`.

const API = "https://ndulchsiqutxibiwzzlc.supabase.co/functions/v1/api-reels";
const CLAVE = "705fdf8433d7cb33ffaba7e95333c664bf8fd904bbea4fc5c211cf52f01a7e94";

try {
  const id = String(input.id || "").trim();
  if (!id) {
    return { success: false, statusCode: 400, code: "falta_id",
             message: "Necesito el id que devolvió crear_video, crear_reel o montar_reel." };
  }

  let r;
  try {
    r = await fetch(API + "?id=" + encodeURIComponent(id), { headers: { "x-api-clave": CLAVE } });
  } catch (e) {
    return { success: false, statusCode: 502, code: "sin_conexion",
             message: "No pude consultar cómo va. NO digas que falló ni que se " +
                      "gastaron créditos: no lo sabemos. Volvé a intentar." };
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
  // acá hay algo que decidir, no algo que reintentar.
  if (d.estado === "rechazado") {
    return { success: false, statusCode: 402, code: "tope_de_creditos",
             message: "No se generó porque supera el tope de gasto por pieza. " +
                      (d.mensaje || "") + " Contáselos así: no falló nada y NO " +
                      "se gastó nada, hay un límite puesto a propósito y para " +
                      "pasarlo alguien lo tiene que subir." };
  }

  if (d.estado === "error") {
    // Un montaje no gastó nada, así que reintentar es gratis y el mensaje suele
    // decir exactamente qué arreglar del guion. Decirle a la persona que se
    // gastaron créditos sería falso y la frenaría por nada.
    return { success: false, statusCode: 500, code: "reel_fallido",
             message: (d.mensaje || "No se pudo hacer.") +
                      (montado
                        ? " Esto era un montaje, así que NO se gastó ningún crédito " +
                          "y reintentarlo es gratis. Si el mensaje de arriba dice qué " +
                          "está mal del guion, arreglalo y volvé a llamar a " +
                          "`montar_reel` vos mismo, sin molestar a la persona."
                        : " Contáselos tal cual. Ojo: es probable que ya se haya " +
                          "cobrado, así que NO lo vuelvas a pedir automáticamente — " +
                          "preguntá si quieren reintentarlo.") };
  }

  if (!d.listo) {
    const seg = d.esperando_seg || 0;
    const demorado = seg > (montado ? 300 : 900);
    return {
      success: true, listo: false, id: id, estado: d.estado, esperando_seg: seg,
      message: demorado
        ? "Lleva " + Math.round(seg / 60) + " minutos, mucho más de lo normal. " +
          "Deciles que hubo una demora y que lo estamos revisando."
        : (montado
            ? "El video se está montando (van " + seg + " segundos). Esto NO es un " +
              "error. Un montaje suele estar en menos de un minuto: volvé a llamar " +
              "a estado_reel con el mismo id, ahora mismo. NO inventes el link."
            : "El " + que + " sigue generándose (van " + seg + " segundos de los " +
              "«unos cinco minutos» que tarda). Esto NO es un error, es lo " +
              "esperable. Volvé a llamar a estado_reel con el mismo id, ahora " +
              "mismo — la consulta espera un minuto adentro, así que van a hacer " +
              "falta unas cinco llamadas en total y está bien que sea así. NO " +
              "inventes el link ni describas cómo quedó."),
    };
  }

  // ── Se pidió el VIDEO: lo que hay es un archivo ──────────────────────
  //
  // Y lo importante que sigue: ese archivo se puede usar. Es una URL pública,
  // así que `montar_reel` lo toma como un clip más — con el título que la
  // persona quiera, mezclado con material filmado, o cortado. Sin volver a
  // pagar la generación.
  if (soloVideo) {
    return {
      success: true, listo: true, id: id, pieza: "video",
      video: d.video_crudo, proveedor: d.proveedor || null,
      message:
        "El video está listo. Pasales el link TAL CUAL viene, sin acortarlo. Es " +
        "el archivo crudo: no tiene título ni música encima, que es lo que se " +
        "pidió. Deciles que lo MIREN ENTERO antes de usarlo — lo genera una IA y " +
        "en los planos de movimiento a veces deforma caras y manos. Si les " +
        "sirve y ahora quieren la pieza para publicar, NO hay que generarlo de " +
        "nuevo ni volver a pagarlo: llamá a `montar_reel` con este mismo link en " +
        "`clips` y el título que quieran. Si el video no les gustó, pedirlo de " +
        "nuevo sí vuelve a costar — avisáselos antes.",
    };
  }

  // Si el montaje no pudo dibujar el texto encima, o no encontró la pista, el
  // video SALE IGUAL y la nota dice por qué. Eso no es un fallo —el clip está y
  // se puede publicar— pero la persona tiene que enterarse antes de subirlo.
  const aviso = d.mensaje ? " OJO: " + d.mensaje + " — decíselo antes de que lo suba." : "";

  return {
    success: true, listo: true, id: id, video: d.url, montado: montado,
    pieza: "reel",
    video_crudo: d.video_crudo || null,
    titulo: d.titulo || null,
    message: "El reel está listo. Pasales el link TAL CUAL viene, sin acortarlo. " +
             "Es un MP4 vertical de 1080×1920 listo para subir a Instagram." + aviso +
             (montado
               ? " Está armado con el material que mandaron: no hay nada inventado " +
                 "por una IA adentro, así que no les adviertas sobre caras ni manos " +
                 "deformadas — no aplica. NO gastó créditos. Deciles igual que lo " +
                 "miren antes de publicar, por si algún corte quedó en un momento " +
                 "raro; si hay que ajustar un tramo o un subtítulo, corregí el guion " +
                 "y volvé a montarlo, que es gratis."
               : " Deciles que lo MIREN ENTERO antes de publicar: el video lo genera " +
                 "una IA y en los planos de movimiento a veces deforma caras y manos. " +
                 (d.video_crudo
                   ? "Si les gusta el video pero no el título o la música, NO hay que " +
                     "volver a generarlo ni a pagarlo: guardaste aparte el archivo sin " +
                     "nada encima (`video_crudo`) y `montar_reel` lo vuelve a armar " +
                     "con otro texto, gratis. "
                   : "") +
                 "Si lo que no funciona es el video mismo, se puede volver a pedir " +
                 "con el pedido corregido — avisales que ese intento sí gasta."),
  };
} catch (e) {
  return {
    success: false, statusCode: 500, code: "error_interno",
    message:
      "Se me rompió la herramienta al consultar: " + String(e) + ". NO inventes " +
      "el link ni digas que falló el video: no lo sabemos. Volvé a intentar.",
  };
}
