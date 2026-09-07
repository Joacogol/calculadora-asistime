// Una puerta angosta para SUBIR un archivo al almacenamiento de la marca.
//
// Existe por una sola razón: desde afuera nadie tiene la service_role —ni
// debería—, y sin ella no se puede escribir en el bucket. Esta función sí la
// tiene (Supabase se la da en el entorno) y la usa para una cosa nada más:
// firmar una URL de subida de un solo uso, para una ruta que ELLA elige.
//
// Quien llama no manda bytes por acá: recibe la URL firmada y sube directo al
// almacenamiento. Así el archivo puede pesar lo que pese sin pasar por la
// función, que tiene un tope de cuerpo chico.
//
// Sólo escribe bajo `proxies/`: copias livianas de videos largos para que un
// modelo las mire. Una clave filtrada, en el peor caso, llena esa carpeta.
// No puede leer, borrar ni pisar nada más.
//
// Se autentica como sus hermanas (`api-reels`, `api-fotos`): `x-api-clave`
// contra el secreto API_CLAVE del proyecto.
import { createClient } from "jsr:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-api-clave",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (b: unknown, s = 200) =>
  new Response(JSON.stringify(b), {
    status: s,
    headers: { ...CORS, "Content-Type": "application/json" },
  });

const BUCKET = "disenos";
const CARPETA = "proxies";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ error: "sólo POST" }, 405);

  const esperada = Deno.env.get("API_CLAVE");
  if (!esperada) return json({ error: "falta configurar API_CLAVE" }, 500);
  const dada = req.headers.get("x-api-clave") || "";
  if (dada !== esperada) return json({ error: "clave inválida" }, 401);

  let cuerpo: { nombre?: string } = {};
  try {
    cuerpo = await req.json();
  } catch {
    return json({ error: "el cuerpo tiene que ser JSON" }, 400);
  }
  // El nombre lo saneamos nosotros: sin barras, sin `..`, sin nada que no sea
  // letra, número, guion, punto o guion bajo. La ruta la arma esta función.
  const crudo = String(cuerpo.nombre || "").trim();
  const nombre = crudo.replace(/[^A-Za-z0-9._-]/g, "_").replace(/\.{2,}/g, ".");
  if (!nombre || nombre.length > 120 || !/\.(mp4|mov|webm|m4a|mp3|wav|json)$/i.test(nombre)) {
    return json({ error: "nombre inválido: tiene que terminar en .mp4/.mov/.webm/.m4a/.mp3/.wav/.json" }, 400);
  }
  const ruta = `${CARPETA}/${nombre}`;

  const base = Deno.env.get("SUPABASE_URL")!;
  const llave = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const sb = createClient(base, llave);

  // `upsert: true` para poder reemplazar una copia por otra con el mismo
  // nombre sin tener que borrar antes: esto es una carpeta de trabajo.
  const { data, error } = await sb.storage.from(BUCKET)
    .createSignedUploadUrl(ruta, { upsert: true });
  if (error || !data) {
    return json({ error: `no pude firmar la subida: ${error?.message || "?"}` }, 500);
  }
  const { data: pub } = sb.storage.from(BUCKET).getPublicUrl(ruta);
  return json({
    ruta,
    subir_a: data.signedUrl,
    token: data.token,
    url_publica: pub.publicUrl,
    como: "PUT del archivo a `subir_a` con el header `x-upsert: true`. Después queda en `url_publica`.",
  });
});
