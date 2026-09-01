// Prueba las tools de Asistime contra la API de verdad.
//
//     deno run -A herramientas/probar-tools-reels.ts
//
// El sandbox de Asistime no se puede reproducir acá, pero sí se puede correr
// el MISMO código de la tool contra el MISMO `index.ts` que se despliega, con
// un Supabase de mentira detrás. Eso cubre lo que más se rompió hasta ahora:
// que la tool lea mal la respuesta de la API.
//
// El 31/8/2026 `ver_reel` devolvía «Error» en el simulador mientras la API
// registraba un 200 limpio. Nunca se pudo reproducir el sandbox, y la lección
// fue envolver todo en un try — pero también que el pegamento entre la tool y
// la API merece una prueba, porque es donde vive el error que no se ve.
//
// Lo que NO prueba: el sandbox de Asistime (su `input`, sus límites de tiempo)
// y la API de los proveedores de video. Eso se prueba pidiendo un video.

const PUERTO_FALSO = 8891;
const PUERTO = 8890;
const CLAVE = "clave-de-prueba";

const filas = new Map<string, Record<string, unknown>>();
let proximoId = 1;

const falso = Deno.serve({ port: PUERTO_FALSO, onListen: () => {} }, (req) => {
  const u = new URL(req.url);
  const json = (b: unknown) =>
    new Response(JSON.stringify(b), { headers: { "Content-Type": "application/json" } });
  if (u.pathname === "/rest/v1/reels" && req.method === "POST") {
    return req.json().then((c) => {
      const id = `00000000-0000-0000-0000-00000000000${proximoId++}`;
      const f = { id, estado: "pendiente", creado_en: new Date().toISOString(), ...c };
      filas.set(id, f);
      return json([f]);
    });
  }
  if (u.pathname === "/rest/v1/reels" && req.method === "GET") {
    const q = u.searchParams.get("id");
    if (q?.startsWith("eq.")) {
      const f = filas.get(q.slice(3));
      return json(f ? [f] : []);
    }
    return json([]);
  }
  return json({ error: "el falso no sabe " + u.pathname });
});

Deno.env.set("API_CLAVE", CLAVE);
Deno.env.set("SUPABASE_URL", `http://localhost:${PUERTO_FALSO}`);
Deno.env.set("SUPABASE_SERVICE_ROLE_KEY", "service-de-mentira");
Deno.env.set("REELS_POR_HORA", "0");

const serveReal = Deno.serve;
// deno-lint-ignore no-explicit-any
(Deno as any).serve = (h: any) => serveReal({ port: PUERTO, onListen: () => {} }, h);
await import(new URL("../funciones/api-reels/index.ts", import.meta.url).href);

// ── Correr una tool como la corre Asistime ────────────────────────────────
//
// El código de la tool es el cuerpo de una función async con un `input` en el
// alcance. Se apuntan la URL y la clave al servidor local: lo que se prueba es
// la lógica, no a qué host le pega.
async function correrTool(archivo: string, input: Record<string, unknown>) {
  let js = await Deno.readTextFile(
    new URL(`../tools-asistime/${archivo}`, import.meta.url));
  js = js.replace(/const API = "[^"]*";/, `const API = "http://localhost:${PUERTO}";`)
         .replace(/const CLAVE = "[^"]*";/, `const CLAVE = "${CLAVE}";`);
  const fn = new Function("input", `return (async () => {\n${js}\n})();`);
  return await fn(input) as Record<string, unknown>;
}

let fallos = 0;
function ok(c: unknown, que: string, detalle?: unknown) {
  if (c) console.log("  ✓", que);
  else { fallos++; console.log("  ✗", que, detalle === undefined ? "" : JSON.stringify(detalle)); }
}

const PEDIDO = "la paleta apoyada en el pasto que crece como un árbol";
const FOTO = "https://ejemplo.com/paleta.jpg";

console.log("\n■ crear_video pregunta con qué sistema antes de gastar");
{
  const d = await correrTool("crear_video.js", { mensaje: PEDIDO, foto: FOTO });
  ok(d.success === true, "no lo cuenta como un error", d);
  ok(d.falta_elegir === "proveedor", "dice qué falta", d.falta_elegir);
  const ops = (d.opciones ?? []) as Record<string, unknown>[];
  ok(ops.length === 2, "con las dos opciones", ops.length);
  ok(ops.every((o) => o.desde && o.duracion && o.sistema),
    "cada una con sistema, precio y duración", ops);
  ok(String(d.message).includes("no se gastó nada"),
    "y le dice al agente que todavía no se gastó nada");
  ok(filas.size === 0, "no se anotó ningún pedido", [...filas.keys()]);
}

console.log("\n■ crear_video con la elección hecha");
let idVideo = "";
{
  const d = await correrTool("crear_video.js",
    { mensaje: PEDIDO, foto: FOTO, proveedor: "magnific", quien: "Joaquín" });
  idVideo = String(d.id ?? "");
  ok(d.success === true && d.id, "encarga", d);
  const f = filas.get(idVideo)!;
  ok((f.metricas as Record<string, unknown>)?.pieza === "video",
    "pidiendo el VIDEO, no la pieza", f.metricas);
  ok(String(d.message).includes("montar_reel"),
    "y le cuenta al agente cómo usarlo después sin volver a pagar");
}

console.log("\n■ crear_reel también pregunta");
let idReel = "";
{
  const d0 = await correrTool("crear_reel.js",
    { mensaje: PEDIDO, foto: FOTO, titulo: "Un título" });
  ok(d0.falta_elegir === "proveedor", "sin proveedor, pregunta", d0.falta_elegir);
  ok(filas.size === 1, "sin anotar nada", filas.size);

  const d = await correrTool("crear_reel.js",
    { mensaje: PEDIDO, foto: FOTO, titulo: "Un título", proveedor: "fal" });
  idReel = String(d.id ?? "");
  ok(d.success === true && d.id, "con proveedor, encarga", d);
  ok(d.proveedor === "fal", "con el que se eligió", d.proveedor);
  ok(String(d.message).includes("fal.ai"), "y lo dice en el mensaje", d.message);
  const f = filas.get(idReel)!;
  ok(f.titulo === "Un título", "guardando el título", f.titulo);
}

console.log("\n■ estado_reel: un VIDEO terminado entrega el archivo");
{
  Object.assign(filas.get(idVideo)!,
    { estado: "listo", url: null, clip_url: "https://base/crudo.mp4" });
  const d = await correrTool("estado_reel.js", { id: idVideo });
  ok(d.listo === true, "dice que está", d);
  ok(d.pieza === "video", "y que es un video", d.pieza);
  ok(d.video === "https://base/crudo.mp4", "con el archivo", d.video);
  const m = String(d.message);
  ok(m.includes("montar_reel") && m.includes("NO hay que generarlo de nuevo"),
    "y le dice que la pieza se arma desde acá sin volver a pagar", m);
}

console.log("\n■ estado_reel: una PIEZA terminada entrega el reel");
{
  Object.assign(filas.get(idReel)!,
    { estado: "listo", url: "https://base/reel.mp4", clip_url: "https://base/reel-crudo.mp4" });
  const d = await correrTool("estado_reel.js", { id: idReel });
  ok(d.listo === true && d.video === "https://base/reel.mp4", "el reel", d.video);
  ok(d.pieza === "reel", "marcado como pieza", d.pieza);
  ok(d.video_crudo === "https://base/reel-crudo.mp4",
    "y además el crudo, para rehacer el título gratis", d.video_crudo);
}

console.log("\n■ estado_reel: mientras genera, no inventa nada");
{
  const nuevo = await correrTool("crear_video.js",
    { mensaje: PEDIDO, foto: FOTO, proveedor: "fal" });
  const d = await correrTool("estado_reel.js", { id: String(nuevo.id) });
  ok(d.listo === false, "dice que todavía no", d.listo);
  ok(!d.video, "y no entrega ningún link", d.video);
}

console.log("\n■ un id que no existe");
{
  const d = await correrTool("estado_reel.js", { id: "no-existe" });
  ok(d.success === false && d.code === "no_existe", "se dice claro", d);
}

console.log(fallos ? `\n✗ ${fallos} fallo(s)\n` : "\n✓ todo bien\n");
await falso.shutdown();
Deno.exit(fallos ? 1 : 0);
