// ═══════════════════════════════════════════════════════════════════════
//  crear_video (Larrique) — video generado con IA, y sólo de AMBIENTE
// ═══════════════════════════════════════════════════════════════════════
//
//  Es la versión de Larrique de la tool 2159 de Asistime, y se guarda aparte
//  por una sola razón, que es la más importante de todo este kit: para este
//  cliente la IA NO puede dibujar el producto.
//
//  El manual 2026 lo pide con todas las letras: «en productos específicos la
//  forma, marca, empaque y detalles técnicos deben coincidir con el producto
//  real». Un rulemán NTN generado por IA sale con la caja mal, el logo torcido
//  y un número de parte inventado, y en este rubro un número de parte
//  inventado es alguien que compra la pieza que no era. Por eso esta tool
//  frena sola cuando el pedido nombra un producto o una marca, y lo dice antes
//  de gastar.
//
//  Lo que sí sirve: el AMBIENTE. El depósito, el pasillo de estanterías, el
//  mostrador, un camión saliendo, el taller, el campo. Ahí no hay nada que
//  falsificar y el video le da a la pieza el movimiento que una foto no tiene.
//
//  Para el PRODUCTO el camino es `montar_reel` con las fotos reales, que no
//  gasta créditos y muestra el rulemán que Larrique de verdad vende.
//
//  No espera el resultado: generar un video son unos cinco minutos y el
//  sandbox corta mucho antes. Devuelve el `id` y después se consulta con
//  `estado_reel`.
//
//  Y no elige el proveedor: si no vino, lo PRIMERO que hace es leer las dos
//  opciones y devolverlas para que la persona elija. Antes que la foto, a
//  propósito — la plata se decide primero y el material después.
//
//  Es la tool 2278 del tenant 80. Sus compañeras son `montar_reel` (2258) y
//  `estado_reel` (2259).

const API = "https://qxjvtxumkljsroukpkny.supabase.co/functions/v1/api-reels";
const CLAVE = "e48ac1d2d7b17611fba71e4450eae31fe326a267c5f7052b72000c484991f1a1";

// Lo que este cliente NO puede pedirle a la IA. Va sin `\b` a propósito: la
// tool viaja como JSON y en el camino `\b` se escapa dos veces y la expresión
// deja de andar sin avisar. Ya pasó una vez con la guarda de fotos de
// `crear_diseno`.
const PRODUCTO = /(rulemán|rulemanes|rodamiento|correa|amortiguador|bomba|embrague|crapodina|homocinétic|reten|retén|repuesto|filtro|buje|cruceta|caja de|el producto|los productos|ntn|fag|ina|luk|skf|continental|timken|koyo|cofap|meclube|enerpac|gates|nsk)/i;

try {
  const mensaje = String(input.mensaje || "").trim();
  if (mensaje.length < 10) {
    return {
      success: false, statusCode: 400, code: "pedido_incompleto",
      message:
        "Todavía no tengo qué tiene que pasar en el video. Escribilo vos: qué " +
        "se ve, cómo se mueve la cámara, con qué luz. No se lo preguntes así a " +
        "la persona — armá la idea con lo que ya dijo y confirmásela. Y acordate " +
        "de que acá el video de IA es de AMBIENTE: el depósito, el mostrador, un " +
        "camión saliendo, el taller, el campo.",
    };
  }

  // ── La regla de marca, antes que la plata ───────────────────────────
  if (PRODUCTO.test(mensaje)) {
    return {
      success: false, statusCode: 400, code: "producto_no_se_genera",
      message:
        "Frené el pedido y NO se gastó nada. Lo que pediste nombra un producto " +
        "o una marca, y para Larrique la IA no puede dibujar eso: el manual " +
        "exige que la forma, la marca, el empaque y los detalles técnicos " +
        "coincidan con el producto real, y ninguna IA acierta un rulemán con su " +
        "caja — sale el logo torcido y un número de parte inventado. En este " +
        "rubro eso es alguien que compra la pieza que no era.\n\n" +
        "Decile a la persona las dos salidas, en tus palabras:\n" +
        "1) Si quiere mostrar EL PRODUCTO: que mande dos o tres fotos reales y " +
        "lo armamos con `montar_reel`, que además no gasta créditos.\n" +
        "2) Si lo que quiere es MOVIMIENTO de fondo: se puede generar el " +
        "ambiente —el depósito, el pasillo de estanterías, el mostrador, un " +
        "camión saliendo, el taller— sin ningún producto identificable a la " +
        "vista. Proponéselo así y volvé a llamarme con el pedido reescrito.",
    };
  }

  // ── Con qué sistema ─────────────────────────────────────────────────
  //
  // Va PRIMERO, antes de pedir la foto, y el orden importa. Estaba al revés y
  // el 1/9/2026 costó 100 créditos: alguien pidió ver los precios antes de
  // decidir, y como la herramienta exigía una foto para llegar a la pregunta,
  // el agente tuvo que encargar una foto —y gastarla— para poder mostrar un
  // precio. La plata se decide primero; el material después.
  //
  // Las opciones se LEEN, no se encargan: esta consulta no anota nada ni gasta
  // nada, así que se puede hacer con el pedido a medio armar.
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
          : " Y avisale en el mismo mensaje que además hace falta una FOTO de " +
            "la que parta el video: que la mande en el chat, o que pase el " +
            "link de una que ya esté publicada en larrique.com.uy. Que decida " +
            "las dos cosas juntas, no una y después la otra.") +
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
        "El video se genera A PARTIR de una foto: sin foto no hay de dónde " +
        "arrancar. Pedile una del ambiente que quiere mover —el depósito, el " +
        "mostrador, el camión— mandada en el chat, o el link de una que ya esté " +
        "publicada en larrique.com.uy. Copiá la URL entera y sin acortarla.",
    };
  }

  const cuerpo = {
    mensaje: mensaje,
    foto: foto,
    pieza: "video",
    quien: input.quien || "Larrique",
  };
  if (input.proveedor) cuerpo.proveedor = String(input.proveedor).trim();

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
        "No pude comunicarme con el estudio. NO digas que se gastó nada: no " +
        "se anotó ningún pedido. Que lo intente de nuevo en unos minutos.",
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
      ". Tarda unos " + Math.round((d.demora_estimada_seg || 300) / 60) +
      " minutos. Avisale a la persona que estás generando el video y después " +
      "consultá `estado_reel` con el id " + d.id + " — van a hacer falta " +
      "varias consultas y eso es normal. Lo que va a volver es el ARCHIVO de " +
      "video, sin título ni música: si después quieren la pieza terminada, se " +
      "arma con `montar_reel` pasando ese mismo archivo junto con las fotos " +
      "reales del producto. NO vuelvas a llamar a `crear_video` por este mismo " +
      "pedido: cada llamada genera y cobra un video nuevo.",
  };
} catch (e) {
  return {
    success: false, statusCode: 500, code: "error_interno",
    message:
      "Se me rompió la herramienta antes de encargar nada: " + String(e) +
      ". NO le digas a la persona que se gastó algo. Avisá al equipo.",
  };
}
