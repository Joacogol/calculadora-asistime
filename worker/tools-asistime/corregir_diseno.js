// ═══════════════════════════════════════════════════════════════════════
//  corregir_diseno — cambiar UNA cosa de una pieza que ya salió
// ═══════════════════════════════════════════════════════════════════════
//
//  Es a `crear_diseno` lo que `retocar_reel` es a `montar_reel`: parte de lo
//  que ya existe en vez de empezar de cero.
//
//  ── Por qué es una tool aparte y no un campo de crear_diseno ───────────
//
//  Porque el campo se olvida. `crear_diseno` de Asistime acepta `corrige`
//  desde el 5/9/2026 y funciona; las de Boss, Stadium y Clínica nunca lo
//  mandaron, así que en tres de los cuatro clientes un pedido de cambio
//  entraba como pedido nuevo: el agente rehacía todo desde el mensaje y volvía
//  OTRA pieza. El 5/9 una story que gustaba se pidió mover la jirafa y volvió
//  con otro fondo, otra tipografía y otro centrado.
//
//  Un verbo propio se elige, un campo opcional se saltea. Y el nombre dice
//  qué hace, que es lo único que el agente lee para decidir.
//
//  ── El id es un UUID y no se inventa ──────────────────────────────────
//
//  La API lo valida y contesta 400 con el motivo. Acá se frena antes, para no
//  gastar el viaje y para que el error se lea en el chat con las palabras que
//  la persona necesita: pedí el link de la pieza.

const API = "PONER-URL-DE-api-disenos";
const CLAVE = "PONER-CLAVE";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const VALIDOS = ["post", "vertical", "story", "reel", "video", "carrusel", "secuencia", "pdf"];

const corrige = String(input.corrige || "").trim();
const mensaje = String(input.mensaje || "").trim();

if (!UUID.test(corrige)) {
  return {
    success: false, statusCode: 400, code: "falta_el_id",
    message:
      "Para corregir necesito el id de la pieza que ya salió, tal cual lo " +
      "devolvió `crear_diseno` cuando la pediste. Buscalo en la conversación. " +
      "Si no está, pedile a la persona el link de la pieza que quiere cambiar. " +
      "NO lo inventes y NO llames a `crear_diseno`: eso devolvería una pieza " +
      "distinta en vez de corregir la que le gusta.",
  };
}

if (mensaje.length < 5) {
  return {
    success: false, statusCode: 400, code: "falta_el_cambio",
    message:
      "Todavía no tengo QUÉ hay que cambiarle. Escribí sólo el cambio, con " +
      "las palabras de la persona: «que el precio se vea más grande», «sacale " +
      "el logo de arriba». No repitas el pedido entero: lo que no se menciona " +
      "se deja tal cual.",
  };
}

const cuerpo = { mensaje: mensaje, corrige: corrige, quien: input.quien || "Asistime" };

// Los formatos de la pieza que se corrige. Si no vienen, la API pone `post`
// por defecto — y una story corregida saldría como post. Por eso el motor,
// cuando corrige, obedece al spec anterior y no a esta lista; mandarlos igual
// evita que el agente lea «post» arriba y se confunda.
const formatos = Array.isArray(input.formatos)
  ? input.formatos.map(String).filter(function (f) { return VALIDOS.indexOf(f) >= 0; })
  : [];
if (formatos.length) cuerpo.formatos = formatos;

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
  return {
    success: false, statusCode: r.status,
    code: datos.codigo || (r.status === 429 ? "sin_saldo" : "error_estudio"),
    message: datos.error || "El estudio rechazó la corrección y no dijo por qué.",
  };
}

return {
  success: true,
  id: datos.id,
  estado: datos.estado,
  corrige: corrige,
  demora_estimada_seg: datos.demora_estimada_seg,
  message:
    "Corrección tomada. Tarda " +
    Math.round((datos.demora_estimada_seg || 150) / 60) +
    " minutos o algo más. Sale la MISMA pieza con ese cambio y nada más. " +
    "Avisale a la persona y después consultá `estado_diseno` con el id " +
    datos.id + " — es un id nuevo, el de la pieza corregida. NO describas " +
    "cómo va a quedar y NO vuelvas a llamar por este mismo cambio.",
};
