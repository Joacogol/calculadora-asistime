// La puerta de entrada para pedir un REEL desde el chat de Asistime.
//
// ── Dos formas de pedirlo, con precios que no se parecen ──────────────────
//
// Con `foto`: un modelo de video INVENTA el clip. Son miles de créditos y unos
// cinco minutos. Es lo que existía desde el principio.
//
// Con `clips` + `guion`: el material YA existe —lo filmó el cliente, lo eligió
// una persona— y el motor lo corta, lo pega, lo encuadra en 9:16 y le pone los
// subtítulos con la tipografía de la marca. **No gasta un solo crédito** y
// tarda menos de un minuto.
//
// Son excluyentes a propósito: entre las dos hay tres órdenes de magnitud de
// diferencia en plata, así que un pedido que trae las dos se rechaza en vez de
// elegir una en silencio.
//
// Hermana de `api-disenos`, y por las mismas razones: la tool no tiene dónde
// guardar secretos, así que lo que queda expuesto en su código es una clave que
// sólo sirve para encargar piezas en UNA base. Si se filtra, lo peor que pasa
// es que alguien encargue reels —que gastan créditos y quedan registrados—, no
// que lea datos ni borre nada.
//
// ── Por qué acá tampoco se espera el reel entero ─────────────────────────
//
// Generar el video son cuatro minutos. Además del timeout hay una razón mejor:
// la tool corre DENTRO del turno del agente, así que esperar todo eso deja el
// chat mudo, y si la conversación se corta en el medio el pedido se pierde con
// ella.
//
// `POST` anota y devuelve el id al instante. `GET` cuenta cómo va — esperando
// hasta un minuto adentro, que no cubre los cinco pero hace que cada consulta
// valga por un minuto en vez de por un instante.

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-api-clave",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
};

// ── Los dos sistemas que pueden generar el video ───────────────────────────
//
// Se pregunta cuál usar ANTES de gastar, y no se elige uno en silencio. No es
// una preferencia técnica: son dos productos distintos —uno cobra en créditos
// y hace hasta 30 segundos, el otro cobra en dólares y hace 5— y quien paga es
// el cliente. Elegir por él es decidir cuánto gasta sin preguntarle.
//
// **El precio de verdad vive en `MODELOS`, en `app/reelero.py`.** Esto es una
// copia para poder decirlo en el chat, porque una función de Supabase no puede
// leer el Python del worker. Una copia se desincroniza sola, así que hay una
// prueba que compara las dos y falla si se separan:
// `herramientas/probar-precios.py`. Si tocás un precio acá o allá, corré eso.
//
// `desde` es lo que sale el video más corto de esa calidad — el número que una
// persona necesita para elegir. El cobro exacto lo calcula el worker con la
// duración real y vuelve en `creditos` cuando el pedido se acepta.
const PROVEEDORES = {
  magnific: {
    nombre: "Magnific (Seedance)",
    moneda: "creditos",
    calidades: {
      borrador: { modelo: "seedance-2-mini", resolucion: "480p", por_segundo: 70 },
      normal: { modelo: "seedance-2-mini", resolucion: "720p", por_segundo: 140 },
      maxima: { modelo: "seedance-2-5-pro", resolucion: "720p", por_segundo: 440 },
    },
    duraciones: "5 o 10 segundos; en calidad máxima, hasta 30",
    demora_estimada_seg: 300,
    nota: "Es el que está probado en producción: todos los videos que salieron " +
      "hasta hoy se hicieron con este.",
  },
  fal: {
    nombre: "fal.ai (MiniMax H3 Max)",
    moneda: "usd",
    calidades: {
      borrador: { modelo: "h3-max", resolucion: "480p", por_segundo: 0.05 },
      normal: { modelo: "h3-max", resolucion: "768p", por_segundo: 0.08 },
      // H3 Max tiene dos resoluciones y nada más. `maxima` y `normal` son la
      // misma: poner tres nombres para dos cosas haría que alguien pague
      // «máxima» creyendo que compró algo distinto.
      maxima: { modelo: "h3-max", resolucion: "768p", por_segundo: 0.08 },
    },
    duraciones: "5 segundos, y nada más",
    demora_estimada_seg: 300,
    nota: "Más barato. Todavía NO se probó con un video real: si falla, el " +
      "pedido se marca con error y no se cobra nada.",
  },
} as const;

type Proveedor = keyof typeof PROVEEDORES;

/** Un sello corto que sólo puede tener quien PREGUNTÓ por las opciones.
 *
 *  ── Por qué las opciones vienen selladas ─────────────────────────────────
 *
 *  Porque decirle al agente «preguntale a la persona» no alcanza, y está
 *  medido: el 1/9/2026, con la instrucción escrita en la herramienta, en el
 *  catálogo y en el prompt, el agente eligió fal por su cuenta y encargó el
 *  video sin preguntar nada. No fue desobediencia: el parámetro declaraba
 *  `enum: ["magnific", "fal"]`, así que sabía los dos valores válidos sin
 *  necesidad de consultar. Un dato que se puede adivinar se adivina.
 *
 *  El sello no se puede adivinar. Sale de la clave de esta función, así que
 *  para tener uno válido hay que haber pedido las opciones — y pedirlas es
 *  gratis, no anota nada, y devuelve el mensaje que dice que hay que
 *  mostrárselas a la persona.
 *
 *  **Lo que esto NO hace:** obligar a que el agente hable con nadie. Puede
 *  pedir las opciones y volver a llamar en el mismo turno. Lo que sí hace es
 *  que no pueda saltearse el paso, que es donde estaba fallando. Del resto se
 *  encarga el mensaje, que ahora sí llega siempre.
 *
 *  Rota cada hora y se aceptan la hora actual y la anterior: un pedido de
 *  video son minutos, no horas, y así un sello nunca vence en el medio de una
 *  conversación por caer justo en el cambio de hora.
 */
async function sello(clave: string, secreto: string, hace = 0): Promise<string> {
  const hora = Math.floor(Date.now() / 3_600_000) - hace;
  const datos = new TextEncoder().encode(`${secreto}|${hora}|${clave}`);
  const hash = await crypto.subtle.digest("SHA-256", datos);
  return Array.from(new Uint8Array(hash).slice(0, 4))
    .map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Las dos opciones escritas para que las lea una persona en un chat. */
async function opcionesDeProveedor(secreto: string) {
  return await Promise.all(
    Object.entries(PROVEEDORES).map(async ([clave, p]) => {
      const plata = (m: number) =>
        p.moneda === "usd" ? `US$ ${m.toFixed(2)}` : `${Math.round(m)} créditos`;
      // Los dos arrancan en 5 segundos, así que ese es el piso comparable.
      const CORTO = 5;
      return {
        clave,
        // Lo que hay que devolver para encargar con este sistema. Va sellado y
        // se manda TAL CUAL: escribir «fal» a secas no alcanza, justamente
        // para que no se pueda elegir sin haber preguntado.
        elegir: `${clave}:${await sello(clave, secreto)}`,
        nombre: p.nombre,
        duraciones: p.duraciones,
        desde: plata(p.calidades.normal.por_segundo * CORTO),
        desde_detalle: `${CORTO} segundos en calidad normal`,
        diez_segundos: clave === "fal"
          ? "no llega: sólo hace 5"
          : plata(p.calidades.normal.por_segundo * 10),
        demora_estimada_seg: p.demora_estimada_seg,
        nota: p.nota,
      };
    }),
  );
}

/** `magnific` | `fal` | null, a partir de lo que mandó la herramienta. */
async function proveedorSellado(dado: string, secreto: string): Promise<Proveedor | null> {
  const [clave, marca] = String(dado).trim().toLowerCase().split(":");
  if (!(clave in PROVEEDORES) || !marca) return null;
  for (const hace of [0, 1]) {
    if (marca === await sello(clave, secreto, hace)) return clave as Proveedor;
  }
  return null;
}

async function preguntaProveedor(secreto: string, extra?: Record<string, unknown>) {
  return {
    codigo: "elegi_proveedor",
    pregunta: "¿Con cuál de los dos sistemas lo genero? Mostrale a la persona " +
      "las dos opciones con su precio y su duración, preguntale cuál prefiere, " +
      "y volvé a llamarme poniendo en `proveedor` el valor de `elegir` TAL " +
      "CUAL viene — no lo escribas de memoria, no sirve. Sin eso no se anota " +
      "nada y no se gasta nada.",
    opciones: await opcionesDeProveedor(secreto),
    ...(extra ?? {}),
  };
}

// Cuántos reels se pueden pedir por hora. Es un freno contra un bucle del chat,
// NO el control de gasto: el que corta por plata es `creditos_maximos` del
// `marca.json`, que mira los créditos de CADA pieza. El techo mensual que
// había se sacó el 28/8/2026 —cuánto gasta el cliente en un mes es decisión
// suya—, así que hoy este tope por hora es el único límite por cantidad.
//
// Empezó en 3 y frenaba antes de que nadie terminara de probar. Lo importante
// es que un tope por hora bajo no ahorra un peso —el que pide doce reels en
// una hora los quería— y en cambio corta una conversación con una persona
// esperando del otro lado.
//
// Se puede cambiar sin tocar código con la variable `REELS_POR_HORA` en
// Supabase. En 0 no hay tope por hora y manda sólo el tope de créditos.
const MAX_POR_HORA = Number(Deno.env.get("REELS_POR_HORA") ?? 12);

// Cuántos clips propios se pueden pegar en un reel. Cada uno se baja entero y
// se recodifica, así que el costo es tiempo de montaje, no plata. Doce tramos
// en 90 segundos son siete segundos y medio cada uno: más que eso ya no es un
// reel editado, es una lista de cortes.
const MAX_CLIPS = Number(Deno.env.get("CLIPS_POR_REEL") ?? 12);

// Cuánto espera el GET a que el reel esté antes de contestar «todavía no».
// Un reel tarda unos cinco minutos, así que la espera no lo cubre entero: lo
// que hace es que cada consulta valga por un minuto en vez de por un instante.
//
// La espera vive ACÁ y no en la tool de Asistime porque el sandbox de las
// tools no sabe dormir: un `setTimeout` no lo suspende, lo mata. Ver la nota
// larga en `api-disenos`.
const ESPERA_MAX_MS = 55_000;
const ESPERA_PASO_MS = 5_000;

const dormir = (ms: number) => new Promise((r) => setTimeout(r, ms));

const json = (b: unknown, s = 200) =>
  new Response(JSON.stringify(b), {
    status: s,
    headers: { ...CORS, "Content-Type": "application/json" },
  });

/** ¿Es una URL que el worker va a poder bajar? Sirve para la foto y para los clips.
 *
 *  Se valida acá y no en el worker porque acá el error todavía le puede llegar
 *  a una persona que puede arreglarlo. Cuatro minutos después, cuando el worker
 *  descubra que la foto no existe, ya se gastaron los créditos.
 */
function urlDescargable(u: string): boolean {
  try {
    const url = new URL(u);
    if (url.protocol !== "https:") return false;
    const h = url.hostname.toLowerCase();
    // Nada de direcciones internas: esta función corre con la service_role y
    // una URL a `localhost` o a una IP privada la convertiría en un ariete
    // contra la red de adentro.
    if (h === "localhost" || h.endsWith(".localhost") || h === "::1") return false;
    if (/^(10\.|127\.|169\.254\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(h)) return false;
    return true;
  } catch {
    return false;
  }
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

  const esperada = Deno.env.get("API_CLAVE");
  if (!esperada) return json({ error: "falta configurar API_CLAVE" }, 500);

  const dada = req.headers.get("x-api-clave") || "";
  if (dada !== esperada) {
    return json({ error: "clave inválida", codigo: "clave_invalida" }, 401);
  }

  const base = Deno.env.get("SUPABASE_URL")!;
  const llave = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const usuario = Deno.env.get("USUARIO_ID") || null;
  const cab = {
    apikey: llave,
    Authorization: `Bearer ${llave}`,
    "Content-Type": "application/json",
  };
  const tabla = `${base}/rest/v1/reels`;

  // ── Cómo va un pedido ──────────────────────────────────────────────────
  if (req.method === "GET") {
    const url0 = new URL(req.url);

    // ── Con qué sistema se puede generar, y qué sale cada uno ────────────
    //
    // Está acá para que el agente pueda mostrar las opciones ANTES de
    // encargar nada, sin tener los precios escritos en el código de la tool
    // —donde quedarían viejos el día que cambien y nadie se enteraría—.
    if (url0.searchParams.get("opciones")) {
      return json({ proveedores: await opcionesDeProveedor(esperada) });
    }

    // ── Qué aprendió la marca ────────────────────────────────────────────
    //
    // Una memoria que no se puede mirar es una memoria en la que no se puede
    // confiar: si un día un reel escribe algo raro, hay que poder ver si es
    // culpa de una corrección vieja y sacarla.
    if (url0.searchParams.get("correcciones")) {
      const r = await fetch(
        `${base}/rest/v1/correcciones?select=de,a,quien,creado_en&order=creado_en.asc`,
        { headers: cab },
      );
      if (!r.ok) return json({ correcciones: [], nota: "esta marca todavía no tiene memoria de correcciones" });
      return json({ correcciones: await r.json() });
    }

    const id = url0.searchParams.get("id");
    if (!id) return json({ error: "falta id" }, 400);
    const esperar = url0.searchParams.get("esperar") !== "no";

    // ── Ver lo que el motor armó, para poder corregirlo ──────────────────
    //
    // Numerado desde 1 y no desde 0, a propósito: estos números los va a
    // decir una persona en un chat («la frase 4 está mal»), y nadie cuenta
    // desde cero fuera de la programación.
    if (url0.searchParams.get("ver")) {
      const r = await fetch(
        `${tabla}?id=eq.${encodeURIComponent(id)}&select=id,estado,url,armado,origen`,
        { headers: cab },
      );
      const filas = await r.json();
      if (!Array.isArray(filas) || !filas.length) {
        return json({ error: "no existe", codigo: "no_existe" }, 404);
      }
      const f = filas[0];
      const a = (f.armado ?? {}) as Record<string, unknown>;
      if (!f.armado) {
        return json({
          error: f.estado === "listo"
            ? "este reel se armó antes de que el motor guardara su guion, así " +
              "que no hay nada que mostrar ni que corregir. Pedilo de nuevo y " +
              "el nuevo sí se va a poder retocar."
            : `todavía no hay nada que ver: el reel está en «${f.estado}».`,
          codigo: "sin_armado",
        }, 409);
      }
      const tramos = (a.tramos ?? []) as Record<string, unknown>[];
      const subs = (a.subtitulos ?? []) as Record<string, unknown>[];
      return json({
        id: f.id,
        estado: f.estado,
        url: f.url || null,
        origen: f.origen || null,
        hook: a.hook ?? "",
        cierre: a.cierre ?? "",
        tramos: tramos.map((t, i) => ({
          n: i + 1,
          archivo: t.archivo,
          desde: t.desde,
          hasta: t.hasta,
        })),
        subtitulos: subs.map((x, i) => ({
          n: i + 1,
          desde: x.desde,
          hasta: x.hasta,
          texto: x.texto,
        })),
      });
    }

    const hasta = Date.now() + (esperar ? ESPERA_MAX_MS : 0);
    for (;;) {
      const r = await fetch(
        `${tabla}?id=eq.${encodeURIComponent(id)}&select=id,estado,url,notas,` +
          `creditos_estimados,creado_en,titulo,clips,clip_url,metricas`,
        { headers: cab },
      );
      const filas = await r.json();
      if (!Array.isArray(filas) || !filas.length) {
        return json({ error: "no existe", codigo: "no_existe" }, 404);
      }
      const f = filas[0];
      const terminado = ["listo", "error", "rechazado"].includes(f.estado);
      const met = (f.metricas ?? {}) as Record<string, unknown>;
      // Qué se pidió: el material o la pieza. La tool lo necesita para no
      // decir cualquier cosa — a quien pidió un VIDEO no se le anuncia «tu
      // reel está listo» y se le manda un archivo con un título encima que no
      // pidió, ni se le ofrece publicarlo tal cual.
      const pieza = met.pieza === "video" ? "video" : "reel";
      const cuerpo = {
        id: f.id,
        estado: f.estado,
        listo: f.estado === "listo",
        terminado,
        pieza,
        proveedor: (met.proveedor as string) ?? null,
        // De cuál de los dos caminos salió. Lo lee la tool para no decir
        // cualquier cosa: un reel MONTADO con material del club no lo generó
        // ninguna IA, así que la advertencia sobre caras y manos deformadas
        // —correcta para el otro camino— ahí sería lisa y llanamente falsa.
        montado: Array.isArray(f.clips) && f.clips.length > 0,
        url: f.url || null,
        // El video GENERADO, sin rótulo ni música: el material crudo.
        //
        // Existe porque «hacé un video» y «hacé un reel» son dos pedidos
        // distintos que hasta ahora tenían una sola salida. Quien pide un
        // video muchas veces lo quiere para usarlo DESPUÉS —en otra pieza, en
        // un reel con otra frase, editado con material propio— y lo que le
        // llegaba era un reel cerrado con título y música encima.
        //
        // Cuando `pieza` es «video» esto es TODO el resultado: `url` queda en
        // null porque no se armó ninguna pieza, y este archivo es lo que se
        // pidió.
        //
        // Dos condiciones para mostrarlo, y las dos por la misma razón —que
        // el link que se entrega tiene que servir mañana—:
        //
        // · sólo en los generados: en un montaje `clip_url` no existe, y el
        //   crudo es material que la persona ya tiene;
        // · sólo cuando el pedido terminó: mientras está en «montando»,
        //   `clip_url` todavía apunta al CDN del proveedor con una firma que
        //   vence —una de Magnific duró 53 minutos—. El worker recién lo pisa
        //   con la copia nuestra al guardar. Un link que vence entregado como
        //   si fuera permanente es peor que no darlo.
        video_crudo: (Array.isArray(f.clips) && f.clips.length) ||
            f.estado !== "listo"
          ? null
          : (f.clip_url || null),
        titulo: f.titulo || null,
        creditos: f.creditos_estimados || null,
        // Lo que salió, CON su unidad al lado. `creditos` sólo puede hablar de
        // Magnific —es una columna entera que se llama créditos—, así que un
        // video de fal se veía como «creditos: null» y parecía gratis. Acá
        // viene el monto en la moneda que corresponda.
        costo: (met.costo as Record<string, unknown>) ?? null,
        mensaje: f.notas || null,
        esperando_seg: Math.round(
          (Date.now() - new Date(f.creado_en).getTime()) / 1000,
        ),
      };
      if (terminado || Date.now() >= hasta) return json(cuerpo);
      await dormir(ESPERA_PASO_MS);
    }
  }

  if (req.method !== "POST") return json({ error: "método no permitido" }, 405);

  // ── Anotar un pedido ───────────────────────────────────────────────────
  let c: Record<string, unknown>;
  try {
    c = await req.json();
  } catch {
    return json({ error: "cuerpo inválido" }, 400);
  }

  // ── Olvidar una corrección ───────────────────────────────────────────────
  //
  // Existe porque la memoria es útil justamente cuando se puede deshacer. Una
  // corrección mal anotada —«que donde diga X diga Y» dicho para un solo
  // reel— si no, ensucia todos los que vengan y nadie sabe por qué.
  const olvidar = String(c.olvidar ?? "").trim();
  if (olvidar) {
    const r = await fetch(
      `${base}/rest/v1/correcciones?de=eq.${encodeURIComponent(olvidar)}`,
      { method: "DELETE", headers: { ...cab, Prefer: "return=representation" } },
    );
    if (!r.ok) return json({ error: "no se pudo olvidar", detalle: await r.text() }, 500);
    const fuera = await r.json();
    return json({
      olvidadas: Array.isArray(fuera) ? fuera.length : 0,
      nota: Array.isArray(fuera) && fuera.length
        ? `ya no voy a cambiar «${olvidar}» por nada.`
        : `no tenía anotada ninguna corrección para «${olvidar}».`,
    });
  }

  // ── Retocar un reel que ya salió ─────────────────────────────────────────
  //
  // No rehace el reel: le cambia lo que se pidió cambiar. Toma el guion que el
  // motor guardó la vuelta anterior —tramos, frases y hook YA resueltos— y
  // anota qué corregir encima. Por eso un retoque **no vuelve a escuchar el
  // audio**: si lo hiciera, volvería a equivocarse exactamente igual (el
  // modelo es determinista con el mismo audio) y de paso tiraría las frases
  // que estaban bien.
  //
  // Y NO pisa el original: crea una fila nueva que apunta a él con `origen`.
  // Una corrección que salió peor no tiene que llevarse puesto lo que ya
  // estaba bien.
  const retocar = String(c.retocar ?? "").trim();
  if (retocar) {
    const cambios = (c.cambios && typeof c.cambios === "object")
      ? c.cambios as Record<string, unknown>
      : null;
    if (!cambios || !Object.keys(cambios).length) {
      return json({
        // El ejemplo no nombra ninguna marca. Este mismo archivo corre para
        // todos los clientes, y explicarle algo a Stadium con el nombre de
        // Boss no sólo queda raro: enseña que el sistema es de otro.
        error: "falta `cambios`: qué corregir. Por ejemplo " +
          `{"reemplazar":[{"de":"como lo escuchó","a":"como se escribe"}]}, ` +
          `{"subtitulos":[{"n":4,"texto":"la frase corregida"}]}, ` +
          `{"hook":"otro hook"} o {"quitar":[3]}.`,
        codigo: "sin_cambios",
      }, 400);
    }

    const r0 = await fetch(
      `${tabla}?id=eq.${encodeURIComponent(retocar)}&select=id,estado,armado,clips,titulo`,
      { headers: cab },
    );
    const filas = await r0.json();
    if (!Array.isArray(filas) || !filas.length) {
      return json({ error: "ese reel no existe", codigo: "no_existe" }, 404);
    }
    const orig = filas[0];
    if (!orig.armado) {
      return json({
        error: orig.estado === "listo"
          ? "ese reel se armó antes de que el motor guardara su guion, así que " +
            "no se puede retocar. Pedilo de nuevo y el nuevo sí."
          : `ese reel todavía está en «${orig.estado}»: no hay nada armado que ` +
            `retocar.`,
        codigo: "sin_armado",
      }, 409);
    }

    // Un chequeo rápido de los números ANTES de anotar nada. La cuenta de
    // verdad la hace el worker en Python —que es donde vive la lógica y donde
    // se recalculan los tiempos al sacar un tramo—, pero un «la frase 40» en
    // un reel de 22 se puede contestar acá mismo, en el momento, en vez de
    // hacer esperar un minuto para decir lo mismo.
    const a = orig.armado as Record<string, unknown>;
    const nSubs = ((a.subtitulos ?? []) as unknown[]).length;
    const nTramos = ((a.tramos ?? []) as unknown[]).length;
    const fuera = (ns: unknown[], tope: number) =>
      ns.filter((n) => !Number.isInteger(n) || (n as number) < 1 || (n as number) > tope);

    const malSub = fuera(
      ((cambios.subtitulos ?? []) as Record<string, unknown>[]).map((x) => x?.n),
      nSubs,
    );
    if (malSub.length) {
      return json({
        error: `no existe la frase número ${malSub.join(", ")}: este reel tiene ` +
          `${nSubs}, del 1 al ${nSubs}.`,
        codigo: "fuera_de_rango",
      }, 400);
    }
    const malTramo = fuera(
      [...((cambios.quitar ?? []) as unknown[]), ...((cambios.orden ?? []) as unknown[])],
      nTramos,
    );
    if (malTramo.length) {
      return json({
        error: `no existe el tramo número ${malTramo.join(", ")}: este reel tiene ` +
          `${nTramos}, del 1 al ${nTramos}.`,
        codigo: "fuera_de_rango",
      }, 400);
    }

    const nueva: Record<string, unknown> = {
      mensaje: String(c.mensaje ?? "").trim() ||
        `Retoque del reel ${retocar}`,
      quien: c.quien ?? "Asistime",
      clips: orig.clips,
      armado: orig.armado,
      guion: { cambios },
      origen: orig.id,
    };
    if (orig.titulo) nueva.titulo = orig.titulo;
    if (usuario) nueva.user_id = usuario;

    const rr = await fetch(tabla, {
      method: "POST",
      headers: { ...cab, Prefer: "return=representation" },
      body: JSON.stringify(nueva),
    });
    if (!rr.ok) {
      return json({ error: "no se pudo anotar el retoque", detalle: await rr.text() }, 500);
    }
    const hecha = (await rr.json())[0];

    // ── Que no haya que corregir lo mismo dos veces ─────────────────────────
    //
    // Un reemplazo casi siempre es un nombre propio que la transcripción
    // entiende mal, y lo entiende mal SIEMPRE igual: «Boss Padel» sale «vos
    // panel» en este reel y en todos los que vengan (ese fue el caso real).
    // Corregirlo una vez y que
    // vuelva a salir mal es la clase de detalle que hace que una herramienta
    // se sienta tonta.
    //
    // Por eso el reemplazo queda anotado y a partir de ahí se aplica solo. El
    // worker lo usa de dos maneras: como vocabulario ANTES de escuchar —que
    // evita el error en vez de taparlo— y como reemplazo después de escribir.
    //
    // `recordar: false` es para el caso contrario, y existe porque no todo
    // reemplazo es una regla: reescribir una frase para que suene mejor en
    // ESTE reel no es cómo se escribe esa palabra siempre.
    const aprender = (cambios.reemplazar ?? []) as Record<string, unknown>[];
    let aprendidas = 0;
    if (cambios.recordar !== false && aprender.length) {
      const filas = aprender
        .map((x) => ({
          de: String(x?.de ?? "").trim(),
          a: String(x?.a ?? "").trim(),
          quien: String(c.quien ?? "Asistime"),
        }))
        .filter((x) => x.de && x.a);
      if (filas.length) {
        // `merge-duplicates` sobre la clave única: corregir de nuevo la misma
        // palabra pisa lo anterior en vez de fallar. Alguien que se corrige a
        // sí mismo tiene razón la segunda vez.
        const ra = await fetch(`${base}/rest/v1/correcciones?on_conflict=de`, {
          method: "POST",
          headers: { ...cab, Prefer: "resolution=merge-duplicates" },
          body: JSON.stringify(filas),
        });
        // Que no se pueda anotar la memoria NO tira abajo el retoque: el reel
        // se corrige igual, sólo que habrá que volver a decirlo la próxima.
        if (ra.ok) aprendidas = filas.length;
        else console.warn("no pude anotar las correcciones:", await ra.text());
      }
    }

    return json({
      id: hecha.id,
      aprendidas,
      estado: hecha.estado,
      origen: orig.id,
      // Un retoque tarda casi lo mismo que un reel: lo que se ahorra es
      // equivocarse de nuevo, no el tiempo de dibujar. Decir menos sería
      // prometer algo que no se cumple.
      demora_estimada_seg: 90,
      cuesta_creditos: false,
    }, 201);
  }

  const mensaje = String(c.mensaje ?? "").trim();
  const foto = String(c.foto ?? "").trim();
  const clips = Array.isArray(c.clips) ? c.clips : [];
  const guion = (c.guion && typeof c.guion === "object") ? c.guion as Record<string, unknown> : null;

  // ── ¿Se pide el MATERIAL o la PIEZA? ─────────────────────────────────────
  //
  //   pieza: "video" → el archivo. Se genera el clip y se entrega tal cual.
  //   pieza: "reel"  → la pieza terminada, con título y música. Lo de siempre.
  //
  // Son dos pedidos distintos y hasta ahora había uno solo. Quien va a editar
  // el video después no quiere un título encima; quien va a publicarlo sí.
  const pieza = String(c.pieza ?? "reel").trim().toLowerCase();
  if (pieza !== "reel" && pieza !== "video") {
    return json({
      error: `«${pieza}» no es nada que sepa hacer: «video» devuelve el ` +
        `archivo crudo para usar después, «reel» arma la pieza con título y ` +
        `música.`,
      codigo: "pieza_invalida",
    }, 400);
  }
  if (pieza === "video" && clips.length) {
    return json({
      error: "`pieza: \"video\"` es para GENERAR un video con IA a partir de " +
        "una foto. Los `clips` son material que ya existe: eso no hay que " +
        "generarlo, ya lo tenés.",
      codigo: "video_con_clips",
    }, 400);
  }

  if (mensaje.length < 10) {
    return json({ error: "el pedido está vacío", codigo: "pedido_incompleto" }, 400);
  }

  // ── Hay dos formas de pedir un reel y son excluyentes ────────────────────
  //
  //   con `clips`  → el material YA existe y sólo hay que editarlo. No gasta
  //                  un crédito: no interviene ningún modelo de video.
  //   con `foto`   → un modelo inventa el video a partir de esa foto. Cuesta
  //                  miles de créditos.
  //
  // La diferencia de precio entre las dos es de tres órdenes de magnitud, así
  // que mandar las dos no se resuelve eligiendo una en silencio: se rechaza y
  // se pregunta. Adivinar acá es adivinar con la plata del cliente.
  if (clips.length && foto) {
    return json({
      error: "llegaron `clips` y `foto` juntos, y son dos pedidos distintos: " +
        "con `clips` se EDITA material que ya existe y no cuesta créditos; con " +
        "`foto` un modelo INVENTA el video y cuesta miles. Mandá uno solo.",
      codigo: "clips_y_foto",
    }, 400);
  }

  if (clips.length) {
    if (clips.length > MAX_CLIPS) {
      return json({
        error: `son ${clips.length} clips y el tope es ${MAX_CLIPS}. Cada uno se ` +
          `baja y se recodifica: más que eso no es un reel, es un problema de ` +
          `tiempo de montaje.`,
        codigo: "demasiados_clips",
      }, 400);
    }
    for (const c0 of clips) {
      const u = typeof c0 === "string" ? c0 : String((c0 as Record<string, unknown>)?.url ?? "");
      if (!urlDescargable(u)) {
        return json({
          error: `«${u.slice(0, 80)}» no sirve como clip: tiene que ser una URL ` +
            `https pública que se pueda descargar.`,
          codigo: "clip_invalido",
        }, 400);
      }
    }
    // **El guion es OPCIONAL, y eso es deliberado.**
    //
    // Al principio esto exigía tramos con `desde` y `hasta`. Era un error: el
    // agente que llama a esta función NO PUEDE VER los videos —recién se
    // escuchan cuando el worker los transcribe—, así que pedirle el segundo
    // exacto en el que empieza lo bueno es pedirle un dato que no tiene, y lo
    // único que podía hacer era inventarlo.
    //
    // Sin guion, el worker usa los clips enteros en orden, les saca los
    // tiempos muertos y los subtitula. Decir los tramos queda para cuando
    // alguien SÍ miró el material —una persona, o el agente diseñador, que ve
    // fotogramas— y sabe qué parte sirve.
  } else {
    if (!foto) {
      return json({
        error: "un reel se arma A PARTIR de una foto, o EDITANDO clips que ya " +
          "existen. Sin una cosa ni la otra no hay reel. La foto puede ser una " +
          "del banco de la marca, una que hayan mandado en el chat, o una " +
          "inventada con `crear_foto`; los clips son videos que mandaron.",
        codigo: "falta_la_foto",
      }, 400);
    }
    if (!urlDescargable(foto)) {
      return json({
        error: "la foto tiene que ser una URL https pública que se pueda descargar",
        codigo: "foto_invalida",
      }, 400);
    }
  }

  // ── Con qué sistema, y que lo elija quien paga ──────────────────────────
  //
  // Sólo en el camino que GENERA. Montar material propio no le pide nada a
  // ningún proveedor, así que preguntarle a alguien cuál usar sería hacerle
  // elegir entre dos cosas que no van a pasar.
  //
  // Sin `proveedor` no se anota nada y se devuelve la pregunta con las dos
  // opciones. Que sea la API la que frena, y no una regla escrita en el
  // prompt, es a propósito: un prompt se puede ignorar en el medio de una
  // conversación larga, y acá lo que está del otro lado es la plata del
  // cliente. La respuesta es 200 y no 400 porque esto no es un error: es una
  // pregunta, y una tool que devuelve error hace que el agente pida disculpas
  // en vez de preguntar.
  let proveedor: Proveedor | null = null;
  if (!clips.length) {
    const p = String(c.proveedor ?? "").trim();
    if (!p) return json(await preguntaProveedor(esperada));
    proveedor = await proveedorSellado(p, esperada);
    if (!proveedor) {
      return json(await preguntaProveedor(esperada, {
        codigo: "proveedor_sin_sello",
        pregunta: `«${p.slice(0, 40)}» no sirve como elección. El valor va con ` +
          `su sello y se copia TAL CUAL del campo \`elegir\` — escribirlo de ` +
          `memoria no alcanza, a propósito: es la forma de que nadie elija por ` +
          `la persona. Mostrale las dos opciones, preguntale, y volvé con la ` +
          `que elija.`,
      }));
    }
  }

  const desde = new Date(Date.now() - 3600_000).toISOString();
  const rc = await fetch(
    `${tabla}?creado_en=gte.${desde}&estado=not.in.(rechazado,error)&select=id`,
    { headers: { ...cab, Prefer: "count=exact" } },
  );
  const recientes = (await rc.json()) as unknown[];
  if (MAX_POR_HORA > 0 && Array.isArray(recientes) &&
      recientes.length >= MAX_POR_HORA) {
    return json({
      error: `ya se pidieron ${recientes.length} reels en la última hora, que es el ` +
        `tope. Cada uno cuesta créditos: si de verdad hacen falta más, hay que ` +
        `subir el tope a propósito (variable REELS_POR_HORA).`,
      codigo: "tope_por_hora",
    }, 429);
  }

  const fila: Record<string, unknown> = { mensaje, quien: c.quien ?? "Asistime" };
  if (clips.length) {
    fila.clips = clips;
    fila.guion = guion ?? {};
  } else {
    fila.foto = foto;
  }

  // Lo que eligió la persona viaja en `metricas`, que es el campo que el
  // worker ya lee de punta a punta. Sin columnas nuevas: una migración por
  // cliente es un paso manual que alguien se olvida de correr en el tercero.
  const met: Record<string, unknown> = {};
  if (proveedor) met.proveedor = proveedor;
  if (pieza === "video") met.pieza = "video";
  if (Object.keys(met).length) fila.metricas = met;

  // Un video crudo no lleva texto encima: no hay dónde ponerlo. Si vinieron,
  // no se guardan en silencio —se avisa—, porque quien los mandó cree que va
  // a verlos y no verlos sin explicación se lee como que algo falló.
  const sobran: string[] = [];
  for (const k of ["titulo", "kicker", "bajada", "musica"]) {
    if (!c[k]) continue;
    if (pieza === "video") sobran.push(k);
    else fila[k] = String(c[k]).trim();
  }
  if (usuario) fila.user_id = usuario;

  const r = await fetch(tabla, {
    method: "POST",
    headers: { ...cab, Prefer: "return=representation" },
    body: JSON.stringify(fila),
  });
  if (!r.ok) {
    return json({ error: "no se pudo anotar el pedido", detalle: await r.text() }, 500);
  }
  const creada = (await r.json())[0];

  return json({
    id: creada.id,
    estado: creada.estado,
    pieza,
    proveedor,
    // Montar material que ya existe es cortar y pegar: no hay que esperar a
    // ningún modelo. Decir 300 acá haría que el agente avise «esto tarda cinco
    // minutos» por algo que sale en menos de uno.
    demora_estimada_seg: clips.length
      ? 60
      : PROVEEDORES[proveedor!].demora_estimada_seg,
    cuesta_creditos: !clips.length,
    // Lo que va a volver cuando termine, dicho ahora para que el agente no
    // prometa lo que no va a llegar.
    devuelve: pieza === "video"
      ? "el archivo de video, sin título ni música (`video_crudo`)"
      : "la pieza terminada, con título y música (`url`)",
    ...(sobran.length
      ? {
        aviso: `un video crudo no lleva texto encima, así que ${sobran.join(", ")} ` +
          `no se usan. Si querés la pieza con título, pedila con ` +
          `\`pieza: "reel"\` — o armala después con este mismo video.`,
      }
      : {}),
  }, 201);
});
