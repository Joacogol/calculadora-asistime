// Prueba de la puerta de entrada de reels, contra un Supabase de mentira.
//
//     deno run -A herramientas/probar-api-reels.ts
//
// Levanta la función DE VERDAD —el mismo `index.ts` que se despliega— con un
// REST falso detrás, y le pega con `fetch`. No se prueba una copia de la
// lógica: se prueba el archivo que va a producción.
//
// ── Por qué esta prueba está escrita al revés de lo cómodo ────────────────
//
// El 1/9/2026 una prueba de publicación pasó contra el código roto, porque el
// Instagram falso decía que sí a todo. Una prueba que no puede fallar no
// prueba nada. Así que acá el falso es DESCONFIADO: guarda lo que se le
// escribe y el test mira ese contenido, en vez de conformarse con un 201.
//
// Y antes de darla por buena hay que correrla contra la versión anterior:
//
//     git show HEAD:worker/funciones/api-reels/index.ts > /tmp/viejo.ts
//
// y comprobar que FALLA. Si pasa con las dos, no está midiendo el cambio.

const PUERTO_FALSO = 8799;
const PUERTO = 8798;
const CLAVE = "clave-de-prueba";

// ── El Supabase de mentira ───────────────────────────────────────────────
//
// Guarda las filas que le insertan y las devuelve. Lo que el test mira es
// ESTO, no el código de respuesta: lo que importa no es que la función haya
// contestado 201, es qué quedó anotado para que el worker lo lea.
const filas = new Map<string, Record<string, unknown>>();
let proximoId = 1;

const falso = Deno.serve({ port: PUERTO_FALSO, onListen: () => {} }, (req) => {
  const u = new URL(req.url);
  const json = (b: unknown, s = 200) =>
    new Response(JSON.stringify(b), {
      status: s,
      headers: { "Content-Type": "application/json" },
    });

  if (u.pathname === "/rest/v1/reels" && req.method === "POST") {
    return req.json().then((cuerpo) => {
      const id = `fila-${proximoId++}`;
      const fila = { id, estado: "pendiente", creado_en: new Date().toISOString(), ...cuerpo };
      filas.set(id, fila);
      return json([fila]);
    });
  }
  if (u.pathname === "/rest/v1/reels" && req.method === "GET") {
    const filtro = u.searchParams.get("id");
    if (filtro?.startsWith("eq.")) {
      const f = filas.get(filtro.slice(3));
      return json(f ? [f] : []);
    }
    // El conteo de la última hora: sin tope para que no moleste.
    return json([]);
  }
  return json({ error: "el falso no sabe " + u.pathname }, 404);
});

Deno.env.set("API_CLAVE", CLAVE);
Deno.env.set("SUPABASE_URL", `http://localhost:${PUERTO_FALSO}`);
Deno.env.set("SUPABASE_SERVICE_ROLE_KEY", "service-de-mentira");
Deno.env.set("REELS_POR_HORA", "0");

// La función se sirve sola al importarse, así que se le dice en qué puerto.
const serveReal = Deno.serve;
// deno-lint-ignore no-explicit-any
(Deno as any).serve = (h: any) => serveReal({ port: PUERTO, onListen: () => {} }, h);
// Con un argumento se prueba OTRO archivo: así se corre esta misma prueba
// contra la versión anterior para comprobar que ahí falla.
const ruta = Deno.args[0]
  ? new URL(Deno.args[0], `file://${Deno.cwd()}/`).href
  : new URL("../funciones/api-reels/index.ts", import.meta.url).href;
void (await import(ruta));

const base = `http://localhost:${PUERTO}`;
const pedir = (metodo: string, cola: string, cuerpo?: unknown) =>
  fetch(base + cola, {
    method: metodo,
    headers: { "x-api-clave": CLAVE, "Content-Type": "application/json" },
    ...(cuerpo ? { body: JSON.stringify(cuerpo) } : {}),
  });

let fallos = 0;
function ok(condicion: unknown, que: string, detalle?: unknown) {
  if (condicion) {
    console.log("  ✓", que);
  } else {
    fallos++;
    console.log("  ✗", que, detalle === undefined ? "" : JSON.stringify(detalle));
  }
}

const FOTO = "https://ejemplo.com/foto.jpg";
const PEDIDO = "un video de la paleta creciendo como un árbol en el parque";

console.log("\n■ Elegir con qué sistema antes de gastar");
{
  const r = await pedir("POST", "/", { mensaje: PEDIDO, foto: FOTO });
  const b = await r.json();
  ok(r.status === 200, "no es un error: es una pregunta", r.status);
  ok(b.codigo === "elegi_proveedor", "pide elegir proveedor", b.codigo);
  ok(Array.isArray(b.opciones) && b.opciones.length === 2, "muestra las dos opciones", b.opciones);
  const claves = (b.opciones ?? []).map((o: Record<string, unknown>) => o.clave);
  ok(claves.includes("magnific") && claves.includes("fal"), "y son Magnific y fal", claves);
  const conPrecio = (b.opciones ?? []).every((o: Record<string, unknown>) => o.desde && o.duraciones);
  ok(conPrecio, "cada una con su precio y su duración");
  ok(filas.size === 0, "y NO se anotó ningún pedido", [...filas.keys()]);
}

console.log("\n■ Un proveedor que no existe no arranca nada");
{
  const r = await pedir("POST", "/", { mensaje: PEDIDO, foto: FOTO, proveedor: "veo" });
  const b = await r.json();
  ok(b.codigo === "proveedor_desconocido", "avisa que no lo conoce", b.codigo);
  ok(Array.isArray(b.opciones), "y vuelve a ofrecer las dos");
  ok(filas.size === 0, "sin anotar nada");
}

console.log("\n■ Las opciones se pueden consultar sin encargar nada");
{
  const r = await pedir("GET", "/?opciones=1");
  const b = await r.json();
  ok(r.status === 200 && b.proveedores?.length === 2, "las devuelve", b);
  const fal = b.proveedores.find((p: Record<string, unknown>) => p.clave === "fal");
  ok(String(fal.duraciones).includes("5"), "y dice que fal sólo hace 5 segundos", fal.duraciones);
  ok(String(fal.diez_segundos).includes("no llega"), "sin prometer diez", fal.diez_segundos);
}

console.log("\n■ Pedir la PIEZA (lo de siempre)");
let idReel = "";
{
  const r = await pedir("POST", "/", {
    mensaje: PEDIDO, foto: FOTO, proveedor: "magnific", titulo: "Un título",
  });
  const b = await r.json();
  idReel = b.id;
  const f = filas.get(b.id)!;
  ok(r.status === 201, "se anota", r.status);
  ok(b.pieza === "reel", "como pieza", b.pieza);
  ok((f.metricas as Record<string, unknown>)?.proveedor === "magnific",
    "con el proveedor que se eligió", f.metricas);
  ok((f.metricas as Record<string, unknown>)?.pieza === undefined,
    "y sin marcar pieza: reel es el default", f.metricas);
  ok(f.titulo === "Un título", "el título se guarda", f.titulo);
  ok(String(b.devuelve).includes("url"), "y promete la pieza", b.devuelve);
}

console.log("\n■ Pedir el VIDEO solo");
let idVideo = "";
{
  const r = await pedir("POST", "/", {
    mensaje: PEDIDO, foto: FOTO, proveedor: "fal", pieza: "video",
    titulo: "un título que sobra", musica: "street",
  });
  const b = await r.json();
  idVideo = b.id;
  const f = filas.get(b.id)!;
  ok(r.status === 201, "se anota", r.status);
  ok((f.metricas as Record<string, unknown>)?.pieza === "video",
    "marcado como video, que es lo que lee el motor", f.metricas);
  ok((f.metricas as Record<string, unknown>)?.proveedor === "fal", "con fal", f.metricas);
  ok(f.titulo === undefined && f.musica === undefined,
    "sin título ni música: un crudo no lleva nada encima", f);
  ok(String(b.aviso ?? "").includes("titulo"), "y avisa que no se usan", b.aviso);
  ok(String(b.devuelve).includes("video_crudo"), "promete el archivo", b.devuelve);
}

console.log("\n■ Montar material propio no pregunta nada");
{
  const r = await pedir("POST", "/", {
    mensaje: "editá estos clips para el feed del club",
    clips: ["https://ejemplo.com/a.mp4"],
  });
  const b = await r.json();
  ok(r.status === 201, "arranca sin elegir proveedor: no interviene ninguno", r.status);
  ok(b.cuesta_creditos === false, "y no cuesta");
}

console.log("\n■ Un video no se pide con material que ya existe");
{
  const r = await pedir("POST", "/", {
    mensaje: PEDIDO, pieza: "video", clips: ["https://ejemplo.com/a.mp4"],
  });
  const b = await r.json();
  ok(r.status === 400 && b.codigo === "video_con_clips", "se rechaza", b);
}

console.log("\n■ El estado dice qué se pidió y entrega lo que corresponde");
{
  // Terminado: el worker ya guardó la copia nuestra.
  Object.assign(filas.get(idVideo)!, {
    estado: "listo", url: null,
    clip_url: "https://base/storage/.../crudo.mp4",
  });
  const b = await (await pedir("GET", `/?id=${idVideo}&esperar=no`)).json();
  ok(b.pieza === "video", "lo marca como video", b.pieza);
  ok(b.proveedor === "fal", "y dice con cuál se hizo", b.proveedor);
  ok(b.video_crudo === "https://base/storage/.../crudo.mp4", "entrega el archivo", b.video_crudo);
  ok(b.url === null, "y no inventa una pieza que nadie armó", b.url);
}
{
  // A medio camino: `clip_url` todavía es el link del proveedor, que vence.
  Object.assign(filas.get(idReel)!, {
    estado: "montando", url: null,
    clip_url: "https://cdn.magnific/firmado-que-vence.mp4",
  });
  const b = await (await pedir("GET", `/?id=${idReel}&esperar=no`)).json();
  ok(b.video_crudo === null,
    "no entrega un link que vence como si fuera permanente", b.video_crudo);
  ok(b.pieza === "reel", "y sigue siendo una pieza", b.pieza);
}

console.log(fallos ? `\n✗ ${fallos} fallo(s)\n` : "\n✓ todo bien\n");
await falso.shutdown();
Deno.exit(fallos ? 1 : 0);
