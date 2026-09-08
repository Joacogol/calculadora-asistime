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

const CARPETA = "proxies";


// ── Quién está llamando ──────────────────────────────────────────────────
//
// Hasta el 7/9/2026 esto era una comparación contra `API_CLAVE`: la función
// vivía en el proyecto de UN cliente, así que saber que la clave era la buena
// alcanzaba para saber en qué base escribir. Con todos los clientes en el
// mismo Supabase eso ya no cierra: la clave además tiene que decir DE QUIÉN
// es, porque de eso dependen el esquema donde vive su base y el bucket donde
// van sus archivos.
//
// Por eso `identificar` devuelve un cliente, no un sí o un no. Y por eso la
// tabla guarda el SHA-256 de la clave y no la clave: si alguien llega a leer
// `public.claves_api` no se lleva las llaves de nadie. La comparación la hace
// Postgres sobre un hash completo, así que no hay tiempo que mirar para
// adivinar la original.
//
// El cliente de la casa —Asistime, que vive en `public`— sigue entrando por
// `API_CLAVE`: no depende de la base para autenticarse, y así una migración
// a medias nunca lo deja afuera.

type Quien = {
  marca: string;
  esquema: string;
  bucket: string;
  usuario: string | null;
};

/** Comparación de largo constante. Con `===` el tiempo de respuesta varía
 *  según cuántos caracteres coinciden, y eso alcanza para adivinar la clave a
 *  fuerza de intentos. */
function misma_clave(dada: string, esperada: string): boolean {
  if (dada.length !== esperada.length) return false;
  let distinto = 0;
  for (let i = 0; i < esperada.length; i++) {
    distinto |= dada.charCodeAt(i) ^ esperada.charCodeAt(i);
  }
  return distinto === 0;
}

async function huella(texto: string): Promise<string> {
  const bytes = await crypto.subtle.digest(
    "SHA-256", new TextEncoder().encode(texto));
  return Array.from(new Uint8Array(bytes))
    .map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function identificar(
  dada: string, base: string, llave: string,
): Promise<Quien | null> {
  if (!dada) return null;

  const propia = Deno.env.get("API_CLAVE") || "";
  if (propia && misma_clave(dada, propia)) {
    return {
      marca: Deno.env.get("MARCA") || "",
      esquema: Deno.env.get("ESQUEMA") || "",
      bucket: Deno.env.get("BUCKET") || "disenos",
      usuario: Deno.env.get("USUARIO_ID") || null,
    };
  }

  const r = await fetch(
    `${base}/rest/v1/claves_resueltas?clave_sha=eq.${await huella(dada)}` +
    `&activa=is.true&select=marca,esquema,bucket,usuario_id&limit=1`,
    { headers: { apikey: llave, Authorization: `Bearer ${llave}` } },
  );
  if (!r.ok) return null;
  let filas: unknown;
  try { filas = await r.json(); } catch { return null; }
  if (!Array.isArray(filas) || !filas.length) return null;
  const f = filas[0] as Record<string, string | null>;
  return {
    marca: f.marca || "",
    esquema: f.esquema || "",
    bucket: f.bucket || "disenos",
    usuario: f.usuario_id || null,
  };
}

/** Las cabeceras con las que se habla con PostgREST. `Accept-Profile` elige el
 *  esquema al leer y `Content-Profile` al escribir; sin ellas se habla con
 *  `public`, que es lo que corresponde para quien tiene proyecto propio. */
function cabeceras(llave: string, esquema: string): Record<string, string> {
  const cab: Record<string, string> = {
    apikey: llave,
    Authorization: `Bearer ${llave}`,
    "Content-Type": "application/json",
  };
  if (esquema) {
    cab["Accept-Profile"] = esquema;
    cab["Content-Profile"] = esquema;
  }
  return cab;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ error: "sólo POST" }, 405);

  const base = Deno.env.get("SUPABASE_URL")!;
  const llave = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

  // Igual que en las demás: la clave dice quién llama, y de eso sale el
  // bucket. Acá no hace falta el esquema —esta función no toca la base— pero
  // sí el bucket: la carpeta de trabajo de un cliente es la suya.
  const quien = await identificar(
    req.headers.get("x-api-clave") || "", base, llave);
  if (!quien) return json({ error: "clave inválida", codigo: "clave_invalida" }, 401);
  const BUCKET = quien.bucket;

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
