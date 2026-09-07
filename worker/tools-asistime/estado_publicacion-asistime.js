// ═══════════════════════════════════════════════════════════════════
//  estado_publicacion — ¿salió de verdad?
// ═══════════════════════════════════════════════════════════════════
//
//  Encolar no es publicar: el worker sube la pieza en el próximo minuto y
//  Meta puede rechazarla. Hasta que esto no diga «publicado», no está
//  publicado — y decirlo antes es prometerle a alguien un posteo que no
//  existe.
//
//  La espera vive del lado de la API, no acá: el sandbox de las tools no sabe
//  dormir —un `setTimeout` no lo suspende, lo mata— así que la consulta se
//  queda esperando adentro hasta 75 segundos. Como el worker corre cada
//  minuto, la mayoría de las veces contesta con el link ya puesto.

const API = "https://qxjvtxumkljsroukpkny.supabase.co/functions/v1/api-publicar";
const CLAVE = "26cfe17eee7b67d8292bcc52f1039ca105f03967c4a1667594b199c7d0b1700e";

const diseno_id = String(input.diseno_id || "").trim();
if (!diseno_id) {
  return {
    success: false, statusCode: 400, code: "falta_diseno_id",
    message: "Necesito el `diseno_id` que devolvió la herramienta de publicar. " +
             "Si publicaste un reel, es el `diseno_id` de la respuesta, NO el " +
             "reel_id.",
  };
}

const url = API + "?diseno_id=" + encodeURIComponent(diseno_id) +
            (input.esperar === false ? "&esperar=no" : "");

let r;
try {
  r = await fetch(url, { headers: { "x-api-clave": CLAVE } });
} catch (e) {
  return {
    success: false, statusCode: 502, code: "sin_conexion",
    message: "No pude consultar cómo va. Probá de nuevo en un minuto; el " +
             "pedido de publicación sigue en pie.",
  };
}

let d = {};
try { d = await r.json(); } catch (e) { d = {}; }

if (!r.ok) {
  return {
    success: false, statusCode: r.status, code: d.codigo || "error_estudio",
    message: d.error || "No pude consultar el estado.",
  };
}

const pubs = d.publicaciones || [];
if (!pubs.length) {
  return {
    success: true, terminado: true, publicaciones: [],
    message: "Este diseño todavía no se mandó a publicar. Si querían " +
             "publicarlo, usá la herramienta de publicar que corresponda.",
  };
}

const publicadas = pubs.filter(function (p) { return p.estado === "publicado"; });
const conError = pubs.filter(function (p) { return p.estado === "error"; });
const links = publicadas.map(function (p) { return p.permalink; })
                        .filter(function (x) { return !!x; });

let message;
if (!d.terminado) {
  message = "Todavía se está subiendo. Volvé a consultar en un minuto y NO " +
            "digas que se publicó hasta que esto diga que sí.";
} else if (conError.length) {
  message = "Instagram rechazó " + conError.length + " de " + pubs.length +
            ". Contale el motivo tal cual: «" +
            (conError[0].mensaje || "sin motivo") + "». No lo reintentes solo.";
} else {
  message = "Publicado" + (links.length ? ". Pasale el link: " + links.join(" ") : ".") +
            " Ahora sí podés decir que salió.";
}

return {
  success: true,
  terminado: d.terminado,
  publicaciones: pubs,
  links: links,
  message: message,
};
