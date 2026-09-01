// ══════════════════════════════════════════════════════════════════════
//  crear_reel — encarga la PIEZA terminada: video + título + música
// ══════════════════════════════════════════════════════════════════════
//
//  Hermana de `crear_video`, y la diferencia es la misma que hay entre
//  `crear_diseno` y `crear_foto`: esto devuelve algo listo para publicar,
//  aquello devuelve material.
//
//  No espera el video: son unos cinco minutos y el sandbox corta mucho
//  antes. Devuelve el `id` y después se consulta con `estado_reel`.
//
//  Y no elige el proveedor. Sin `proveedor` la API contesta 200 con las dos
//  opciones y SIN anotar nada: hay que preguntarle a la persona. Son dos
//  productos con precios y duraciones distintas y el que paga es el cliente.

const API = "https://ndulchsiqutxibiwzzlc.supabase.co/functions/v1/api-reels";
const CLAVE = "705fdf8433d7cb33ffaba7e95333c664bf8fd904bbea4fc5c211cf52f01a7e94";

try {
  const mensaje = String(input.mensaje || "").trim();
  if (mensaje.length < 10) {
    return {
      success: false, statusCode: 400, code: "pedido_incompleto",
      message:
        "Todavía no tengo qué tiene que pasar en el video. Escribilo vos: qué se " +
        "ve, cómo se mueve la cámara, con qué luz. No se lo preguntes así a la " +
        "persona — armá la idea con lo que ya dijo y confirmásela.",
    };
  }

  const foto = String(input.foto || "").trim();
  if (!foto) {
    return {
      success: false, statusCode: 400, code: "falta_la_foto",
      message:
        "Un reel se arma A PARTIR de una foto: sin foto no hay video. Las del " +
        "banco no sirven acá porque no tienen URL pública. Usá una que hayan " +
        "mandado en el chat, o armá la de partida con `crear_foto` (100 " +
        "créditos) — mostrásela antes, porque si no le gusta se pierde también " +
        "el video.",
    };
  }

  const cuerpo = { mensaje: mensaje, foto: foto, quien: input.quien || "Asistime" };
  // `undefined` no se serializa: si no vinieron, la base pone lo que corresponda
  // en vez de recibir un null que pise el default.
  for (const k of ["titulo", "kicker", "bajada", "proveedor"]) {
    if (input[k]) cuerpo[k] = String(input[k]).trim();
  }

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
      message:
        "No pude comunicarme con el estudio. NO digas que se gastaron créditos: " +
        "no se anotó nada. Que lo intente de nuevo en unos minutos.",
    };
  }

  let d = {};
  try { d = await r.json(); } catch (e) { d = {}; }

  // ── Falta elegir con qué sistema ────────────────────────────────────
  //
  // Llega como 200 y no como error, porque no falló nada: falta un dato que
  // sólo puede dar la persona. Las opciones vienen de la API y no están
  // escritas acá — un precio copiado en la tool queda viejo el día que
  // cambie, y nadie se entera hasta la factura.
  if (d.codigo === "elegi_proveedor" || d.codigo === "proveedor_desconocido") {
    const ops = (d.opciones || []).map(function (o) {
      return {
        elegir: o.clave,
        sistema: o.nombre,
        duracion: o.duraciones,
        desde: o.desde + " (" + o.desde_detalle + ")",
        diez_segundos: o.diez_segundos,
        a_tener_en_cuenta: o.nota,
      };
    });
    return {
      success: true,
      falta_elegir: "proveedor",
      opciones: ops,
      message:
        "Antes de gastar hay que elegir con qué sistema se genera el video. NO " +
        "se anotó ningún pedido y no se gastó nada todavía. Mostrale a la " +
        "persona las dos opciones de `opciones` con su precio y su duración, en " +
        "tus palabras y en dos líneas, y preguntale cuál prefiere. Cuando te " +
        "conteste, volvé a llamar a `crear_reel` con exactamente los mismos " +
        "datos, agregando `proveedor`. No elijas vos.",
    };
  }

  if (!r.ok) {
    const codigos = {
      400: "pedido_invalido",
      401: "clave_invalida",
      402: "sin_saldo",
      429: "tope_por_hora",
    };
    return {
      success: false,
      statusCode: r.status,
      code: codigos[r.status] || "error_estudio",
      message: d.error || "El estudio rechazó el pedido y no dijo por qué.",
    };
  }

  return {
    success: true,
    id: d.id,
    estado: d.estado,
    proveedor: d.proveedor,
    demora_estimada_seg: d.demora_estimada_seg,
    message:
      "Pedido tomado con " + (d.proveedor === "fal" ? "fal.ai" : "Magnific") +
      ". El video tarda unos " + Math.round((d.demora_estimada_seg || 300) / 60) +
      " minutos. Avisale a la persona que lo estás armando y después consultá " +
      "`estado_reel` con el id " + d.id + " — van a hacer falta varias " +
      "consultas y eso es normal. NO vuelvas a llamar a crear_reel por este " +
      "mismo pedido: cada llamada genera y cobra un video nuevo.",
  };
} catch (e) {
  return {
    success: false, statusCode: 500, code: "error_interno",
    message:
      "Se me rompió la herramienta antes de encargar nada: " + String(e) +
      ". NO le digas a la persona que se gastaron créditos. Avisá al equipo.",
  };
}
