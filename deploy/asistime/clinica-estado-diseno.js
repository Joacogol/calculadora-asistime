// Consulta inmediata: esperar=no. Sin bucles ni demoras dentro del chat.
const API = "https://jejohzzxxnhktdxpdqpy.supabase.co/functions/v1/api-disenos";
const CLAVE = "CONFIGURAR_EN_ASISTIME";

const id = String(input.id || "").trim();
if (!id) {
  return { success: false, statusCode: 400, code: "falta_id",
           message: "Necesito el id que devolvió crear_diseno." };
}

let r;
try {
  r = await fetch(API + "?id=" + encodeURIComponent(id) + "&esperar=no",
                  { headers: { "x-api-clave": CLAVE } });
} catch (e) {
  return { success: false, statusCode: 502, code: "sin_conexion",
           message: "No pude consultar cómo va la pieza. Decile a la persona " +
                    "que seguí pendiente y volvé a intentar en un minuto. NO " +
                    "digas que falló: no lo sabemos." };
}

if (r.status === 404) {
  return { success: false, statusCode: 404, code: "no_existe",
           message: "No existe ningún pedido de diseño con ese id." };
}
if (!r.ok) {
  return { success: false, statusCode: r.status,
           code: r.status === 401 ? "clave_invalida" : "error_estudio",
           message: "No pude consultar cómo va la pieza." };
}

let d = {};
try { d = await r.json(); } catch (e) {
  return { success: false, statusCode: 502, code: "respuesta_rara",
           message: "El estudio contestó algo que no pude leer." };
}

if (d.estado === "error") {
  return {
    success: false, statusCode: 500, code: "diseno_fallido",
    message: (d.mensaje || "La pieza no se pudo hacer.") +
             " Contáselo a la persona tal cual y ofrecele volver a pedirla " +
             "describiendo lo que quiere de otra forma.",
  };
}

if (!d.listo) {
  const seg = d.esperando_seg || 0;
  const demorado = seg > 900;
  return {
    success: true, listo: false, id: id, estado: d.estado, esperando_seg: seg,
    message: demorado
      ? "El pedido lleva " + Math.round(seg / 60) + " minutos, mucho más de " +
        "lo normal. Decile a la persona que hubo una demora y que lo estamos " +
        "revisando."
      : "La pieza sigue en preparación (van " + seg + " segundos de los dos a " +
        "cuatro minutos que tarda). No es un error. Conservá el mismo id y " +
        "respondé que sigue en preparación. No encadenes consultas en este turno " +
        "ni prometas avisos automáticos. Consultá cuando la persona pregunte otra vez. " +
        "No inventes links ni describas una pieza que todavía no está lista.",
  };
}

const piezas = []
  .concat(d.imagenes || [], d.videos || [], d.documentos || []);

return {
  success: true,
  listo: true,
  id: id,
  titulo: d.titulo || null,
  imagenes: d.imagenes || [],
  videos: d.videos || [],
  documentos: d.documentos || [],
  copy: d.copy || null,
  message: "La pieza está lista: " + piezas.length +
           (piezas.length === 1 ? " archivo." : " archivos.") +
           " Pasale los links TAL CUAL vienen, sin acortarlos ni cambiarlos. " +
           (d.copy ? "Tenés también un texto sugerido para el pie de la " +
                     "publicación; ofrecéselo, no lo impongas. " : "") +
           (d.mensaje ? "Contále además esto: " + d.mensaje + " " : "") +
           "Si quiere cambios, volvé a llamar a crear_diseno con el pedido " +
           "corregido — y si lo que hay que cambiar es el MOLDE y no esta " +
           "pieza puntual, usá crear_plantilla con `corrige`. Si quiere que " +
           "salga en el Instagram de la clínica, usá publicar_diseno — pero " +
           "recién después de que la haya visto y te lo pida.",
};