// ═══════════════════════════════════════════════════════════════════
//  crear_diseno — encarga una pieza para @asistime.ai
// ═══════════════════════════════════════════════════════════════════
//
//  No espera el resultado, y eso es a propósito: un diseño tarda entre 2 y 4
//  minutos —Chromium levanta y renderiza— y el sandbox corta mucho antes. Si
//  esta tool esperara, fallaría SIEMPRE, y encima después de haber gastado el
//  render. Devuelve el `id` al instante y `estado_diseno` cuenta cómo va.
//
//  ── Los formatos son sólo los que esta marca sabe dibujar ──────────────
//
//  Hasta el 3/9/2026 acá no estaban `carrusel` ni `secuencia`: Asistime es
//  una marca de datos y los carruseles necesitaban Python (`DIAPOS`). Desde
//  el kit oficial, sus cinco plantillas —titular, dato, testimonio, producto
//  y cierre— son también sus diapositivas, así que se suman. Sigue sin `pdf`:
//  eso todavía necesita `PRESENTACION`, que es código. Ofrecerlo acá sería
//  prometer una pieza que el motor rechaza cuatro minutos después, con un
//  error que el agente no puede explicar.
//
//  ── Las fotos no se recortan acá ───────────────────────────────────
//
//  Van tal cual y el tope lo pone la API: seis. Y los links de Google Drive
//  sirven en sus tres formas —el de ver, el de descarga y el id pelado—: la
//  API va a buscar los bytes ella misma. Lo único que tiene que estar es la
//  carpeta compartida como «cualquiera con el enlace».

const API = "https://qxjvtxumkljsroukpkny.supabase.co/functions/v1/api-disenos";
const CLAVE = "26cfe17eee7b67d8292bcc52f1039ca105f03967c4a1667594b199c7d0b1700e";
const VALIDOS = ["post", "vertical", "story", "reel", "carrusel", "secuencia"];

const mensaje = String(input.mensaje || "").trim();
if (mensaje.length < 10) {
  return {
    success: false, statusCode: 400, code: "pedido_incompleto",
    message:
      "Todavía no tengo qué tiene que comunicar la pieza. Armá la idea con lo " +
      "que ya dijeron y confirmásela antes de volver a llamar.",
  };
}

let formatos = Array.isArray(input.formatos)
  ? input.formatos.map(String).filter(function (f) { return VALIDOS.indexOf(f) >= 0; })
  : [];
if (!formatos.length) formatos = ["vertical"];

const cuerpo = {
  mensaje: mensaje,
  formatos: formatos,
  quien: input.quien || "Asistime",
};
if (Array.isArray(input.fotos) && input.fotos.length) cuerpo.fotos = input.fotos;
if (Array.isArray(input.fotos_elegidas) && input.fotos_elegidas.length) {
  cuerpo.fotos_elegidas = input.fotos_elegidas;
}

// ── Corregir en vez de rehacer ──────────────────────────────────────────
//
// `corrige` es el id de una pieza que YA se entregó. Con eso, el motor parte
// del spec exacto de esa pieza y cambia sólo lo que se pide.
//
// Sin esto, un pedido de cambio entraba como un pedido nuevo: el agente
// rehacía todo desde el mensaje y volvía OTRA pieza. El 5/9/2026 una story
// que gustaba se pidió mover la jirafa y volvió con otro fondo, otra
// tipografía y otro centrado. Es la misma diferencia que ya existe entre
// `montar_reel` y `retocar_reel`.
if (input.corrige) cuerpo.corrige = String(input.corrige).trim();

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
    message: "No pude comunicarme con el estudio. Que lo intenten de nuevo en unos minutos.",
  };
}

let datos = {};
try { datos = await r.json(); } catch (e) { datos = {}; }

if (!r.ok) {
  const codigos = { 400: "pedido_invalido", 401: "clave_invalida",
                    402: "sin_saldo", 429: "tope_por_hora" };
  return {
    success: false, statusCode: r.status,
    code: datos.codigo || codigos[r.status] || "error_estudio",
    message: datos.error || "El estudio rechazó el pedido y no dijo por qué.",
  };
}

const conFotos = datos.fotos_recibidas
  ? " Me quedé con " + datos.fotos_recibidas +
    (datos.fotos_recibidas === 1 ? " foto suya." : " fotos suyas.") : "";

return {
  success: true,
  id: datos.id,
  estado: datos.estado,
  formatos: datos.formatos,
  fotos_recibidas: datos.fotos_recibidas || 0,
  demora_estimada_seg: datos.demora_estimada_seg,
  message:
    "Pedido tomado (" + (datos.formatos || []).join(", ") + "). Tarda " +
    Math.round((datos.demora_estimada_seg || 150) / 60) + " minutos o algo más." +
    conFotos + " Avisales que la estás armando y después consultá " +
    "`estado_diseno` con el id " + datos.id + ". NO describas cómo va a " +
    "quedar: todavía no existe. NO vuelvas a llamar a crear_diseno por este " +
    "mismo pedido.",
};
