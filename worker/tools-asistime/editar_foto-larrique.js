// ═══════════════════════════════════════════════════════════════════════
//  editar_foto (Larrique) — los seis verbos, con la regla del producto
// ═══════════════════════════════════════════════════════════════════════
//
//  Es la versión de Larrique de la tool 2244 de Life, y se guarda aparte por
//  dos diferencias que no son cosméticas.
//
//  ── 1. Acá SÍ está `crear` ──────────────────────────────────────────
//
//  En Life se dejó afuera porque sus fotos son de socios reales y una cara
//  generada publicada como si fuera un socio es un problema distinto al de una
//  pieza fea. Larrique no fotografía gente: fotografía repuestos, y lo que
//  necesita inventar es AMBIENTE — el pasillo del depósito, el mostrador, el
//  taller—. Ahí no hay nadie a quien suplantar. Y hace falta además para
//  `crear_video`, que necesita una foto de la que partir y este cliente todavía
//  no tiene banco.
//
//  Con el mismo límite de siempre: `crear` no dibuja productos. La guarda es
//  la misma expresión que usa `crear_video`, y frena antes de gastar.
//
//  ── 2. `fondo` es el verbo estrella, y conviene decirlo ─────────────
//
//  Las fotos de catálogo de proveedor llegan casi todas con fondo blanco, y la
//  composición `diagonal` de la plantilla `producto` está hecha para un
//  producto recortado sobre el gris claro. `fondo` es el paso que faltaba
//  entre las dos cosas, y además es el más barato y el único que no redibuja
//  un solo píxel del producto: lo recorta.
//
//  Es la tool 2279 del tenant 80. Su compañera es `estado_foto` (2280).

const API = "https://qxjvtxumkljsroukpkny.supabase.co/functions/v1/api-fotos";
const CLAVE = "CONFIGURAR_EN_ASISTIME";

const VERBOS = ["fondo", "tamano", "formato", "retoque", "escena", "crear"];
const CON_INSTRUCCION = ["retoque", "escena", "crear"];
const SIN_FOTO = ["crear"];
const FORMATOS = ["post", "vert", "story", "reel"];

// Los que REDIBUJAN píxeles del producto en vez de sólo moverlo o recortarlo.
// No se prohíben —una foto de contexto se puede retocar tranquila— pero el
// agente tiene que avisar que hay que mirar el resultado contra el producto
// real antes de publicarlo.
const REDIBUJAN = ["retoque", "escena", "formato"];

// Lo que `crear` no puede inventar. Va sin `\b` a propósito: la tool viaja
// como JSON y en el camino el borde de palabra se escapa dos veces y la
// expresión deja de andar sin avisar. Ya pasó con la guarda de `crear_diseno`.
const PRODUCTO = /(rulemán|rulemanes|rodamiento|correa|amortiguador|bomba|embrague|crapodina|homocinétic|reten|retén|repuesto|filtro|buje|cruceta|caja de|el producto|los productos|ntn|fag|ina|luk|skf|continental|timken|koyo|cofap|meclube|enerpac|gates|nsk)/i;

try {
  const verbo = String(input.verbo || "").trim().toLowerCase();
  if (VERBOS.indexOf(verbo) < 0) {
    return {
      success: false, statusCode: 400, code: "verbo_desconocido",
      message:
        "«" + (verbo || "(vacío)") + "» no es algo que sepa hacer. Puedo: " +
        "fondo (recorta el producto y deja el fondo transparente — el que más " +
        "sirve acá), tamano (agranda una foto chica), formato (la lleva a otra " +
        "proporción inventando los bordes en vez de recortar), retoque (cambia " +
        "o saca algo puntual), escena (lleva el producto a otro lugar) y crear " +
        "(inventa una foto de AMBIENTE desde cero, sin partir de ninguna).",
    };
  }

  const instruccion = String(input.instruccion || "").trim();

  // ── La regla de marca, antes que la plata ───────────────────────────
  //
  // Sólo para `crear`: los otros cinco parten de una foto real del producto,
  // así que no hay nada inventado de cero que pueda salir mal de esta manera.
  if (verbo === "crear" && PRODUCTO.test(instruccion)) {
    return {
      success: false, statusCode: 400, code: "producto_no_se_genera",
      message:
        "Frené el pedido y NO se gastó nada. Lo que pediste nombra un producto " +
        "o una marca, y para Larrique la IA no puede dibujar eso: el manual " +
        "exige que la forma, la marca, el empaque y los detalles técnicos " +
        "coincidan con el producto real, y ninguna IA acierta un rulemán con su " +
        "caja. En este rubro eso es alguien que compra la pieza que no era.\n\n" +
        "Las dos salidas, contáselas en tus palabras:\n" +
        "1) Si hay una foto del producto, mandámela y la mejoro con `fondo` " +
        "(recorte), `tamano` o `formato`, que no inventan nada.\n" +
        "2) Si lo que falta es un FONDO o un ambiente —el depósito, el " +
        "mostrador, el taller, una textura— eso sí se puede crear, sin ningún " +
        "producto identificable a la vista. Reescribí el pedido así y volvé a " +
        "llamarme.",
    };
  }

  const foto = String(input.foto || "").trim();
  if (!foto && SIN_FOTO.indexOf(verbo) < 0) {
    return {
      success: false, statusCode: 400, code: "falta_la_foto",
      message:
        "Necesito la URL de la foto a editar, copiada tal cual de la " +
        "conversación, entera y sin acortar. Si no la mandaron, pedísela — o " +
        "pasá el link de una que ya esté publicada en larrique.com.uy.",
    };
  }

  if (CON_INSTRUCCION.indexOf(verbo) >= 0 && instruccion.length < 4) {
    return {
      success: false, statusCode: 400, code: "falta_la_instruccion",
      message:
        "«" + verbo + "» necesita que le digas qué hacer, con detalle. Sacálo " +
        "de lo que dijo la persona y confirmáselo antes: esto gasta créditos." +
        (verbo === "crear"
          ? " Y acordate de que `crear` es para AMBIENTE: «el pasillo de un " +
            "depósito de repuestos, estanterías metálicas, luz industrial " +
            "fría, sin personas y sin ningún texto ni cartel a la vista»."
          : ""),
    };
  }

  const cuerpo = { verbo: verbo, quien: input.quien || "Larrique" };
  if (foto) cuerpo.foto = foto;
  if (instruccion) cuerpo.instruccion = instruccion;

  // `formato` necesita saber a cuál, y `crear` lo acepta opcional: sin él la
  // foto sale cuadrada, que casi nunca es lo que hace falta acá.
  const fmt = String(input.formato || "").trim().toLowerCase();
  if (verbo === "formato" && FORMATOS.indexOf(fmt) < 0) {
    return {
      success: false, statusCode: 400, code: "falta_el_formato",
      message:
        "Para «formato» hay que decir a cuál: vert (1080x1350, el del feed de " +
        "Larrique), story o reel (bien alta), o post (cuadrada).",
    };
  }
  if (fmt && FORMATOS.indexOf(fmt) >= 0) cuerpo.formato = fmt;

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
        "No pude pedir la edición. Probá de nuevo en un minuto. NO digas que " +
        "la estás haciendo: no se pidió, así que no se gastó nada.",
    };
  }

  let d = {};
  try { d = await r.json(); } catch (e) { d = {}; }

  if (!r.ok) {
    return {
      success: false, statusCode: r.status,
      code: d.codigo || (r.status === 429 ? "tope_por_hora" : "error_estudio"),
      message: d.error || "No se pudo pedir la edición y no sé por qué.",
    };
  }

  const aviso = REDIBUJAN.indexOf(verbo) >= 0
    ? " OJO con este verbo en particular: no mueve la foto, **redibuja** parte " +
      "de la imagen. Si lo que se ve es un producto, mirá que la forma, la " +
      "marca y el empaque sigan siendo los del producto real antes de usarla — " +
      "si cambió algo, no sirve y hay que probar con `fondo` o `tamano`."
    : "";

  return {
    success: true, id: d.id || "", estado: d.estado || "",
    creditos_estimados: d.creditos_estimados || 0,
    message:
      "Edición encargada. Tarda menos de un minuto. Consultá `estado_foto` con " +
      "el id " + (d.id || "") + " — esa consulta espera adentro, así que lo más " +
      "probable es que se la puedas mostrar en este mismo mensaje. Cuando " +
      "vuelva: **mostrásela ANTES de usarla** en una pieza, y recién si les " +
      "gusta pasá esa URL a `crear_diseno` en `fotos`, a `montar_reel` en " +
      "`material` o a `crear_video` en `foto`." + aviso + " NO vuelvas a llamar " +
      "por este mismo pedido: cada llamada cuesta.",
  };
} catch (e) {
  return {
    success: false, statusCode: 500, code: "error_inesperado",
    message: "Se me rompió algo al editar la foto: " + String(e && e.message || e),
  };
}
