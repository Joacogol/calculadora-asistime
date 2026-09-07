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
//  Y no elige el proveedor: si no vino, lo PRIMERO que hace es leer las dos
//  opciones y devolverlas para que la persona elija. Antes que la foto, a
//  propósito — la plata se decide primero y el material después.
//  No es un rodeo: son dos productos con precios, duraciones y monedas
//  distintas, y el que paga es el cliente.

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

  // ── Antes que nada: con qué sistema ─────────────────────────────────
  //
  // Esto va PRIMERO, antes de pedir la foto, y el orden importa. Estaba al
  // revés y el 1/9/2026 costó 100 créditos: alguien pidió ver los precios
  // antes de decidir, y como la herramienta exigía una foto para llegar a la
  // pregunta, el agente tuvo que encargar una foto —y gastarla— para poder
  // mostrar un precio. La plata se decide primero; el material después.
  //
  // Las opciones se LEEN, no se encargan: esta consulta no anota nada ni
  // gasta nada, así que se puede hacer con el pedido a medio armar.
  if (!input.proveedor) {
    let ops = [];
    try {
      const ro = await fetch(API + "?opciones=1", { headers: { "x-api-clave": CLAVE } });
      const d0 = await ro.json();
      ops = (d0.proveedores || []).map(function (o) {
        return {
          // Se copia TAL CUAL: viene sellado y sin el sello no sirve.
          elegir: o.elegir,
          sistema: o.nombre,
          duracion: o.duraciones,
          desde: o.desde + " (" + o.desde_detalle + ")",
          diez_segundos: o.diez_segundos,
          a_tener_en_cuenta: o.nota,
        };
      });
    } catch (e) {
      ops = [];
    }
    return {
      success: true,
      falta_elegir: "proveedor",
      opciones: ops,
      falta_foto: !String(input.foto || "").trim(),
      message:
        "Antes de gastar hay que elegir con qué sistema se genera. NO se anotó " +
        "ningún pedido y no se gastó nada todavía. Mostrale a la persona las " +
        "dos opciones de `opciones` con su precio y su duración, en tus " +
        "palabras y en dos líneas, y preguntale cuál prefiere. No elijas vos: " +
        "es su plata. Cuando te conteste, volvé a llamarme poniendo en " +
        "`proveedor` el valor de `elegir` COPIADO TAL CUAL — escribir «fal» o " +
        "«magnific» de memoria no funciona, y es a propósito." +
        (String(input.foto || "").trim()
          ? ""
          : " Y avisale en el mismo mensaje que además hace falta una foto de " +
            "la que parta el video: puede ser una que mande en el chat, o una " +
            "que armemos con `crear_foto` por 100 créditos. Que decida las dos " +
            "cosas juntas, no una y después la otra.") +
        (ops.length
          ? ""
          : " OJO: no pude leer los precios. Decile que hay dos sistemas " +
            "—Magnific y fal.ai— y que uno cobra en créditos y el otro en " +
            "dólares, pero NO inventes ningún número."),
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

  // La red de atrás: si la elección llegó sin sello —escrita de memoria— la API
  // no anota nada y devuelve las opciones de nuevo. Contesta 200 porque no es
  // un error, es la pregunta otra vez.
  if (d.codigo === "elegi_proveedor" || d.codigo === "proveedor_sin_sello") {
    return {
      success: true,
      falta_elegir: "proveedor",
      opciones: (d.opciones || []).map(function (o) {
        return {
          elegir: o.elegir,
          sistema: o.nombre,
          duracion: o.duraciones,
          desde: o.desde + " (" + o.desde_detalle + ")",
          diez_segundos: o.diez_segundos,
          a_tener_en_cuenta: o.nota,
        };
      }),
      message:
        (d.pregunta || "Falta elegir el sistema.") + " NO se anotó ningún " +
        "pedido y no se gastó nada. Mostrale las dos opciones a la persona, " +
        "preguntale, y volvé con el valor de `elegir` copiado tal cual.",
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
