// ¿Se reconocen los links de Google Drive, y sólo esos?
//
//     deno run -A herramientas/probar-drive.ts
//
// Lo que Drive le da a una persona cuando comparte una foto es la dirección de
// una PÁGINA, no la de la imagen. El 1/9/2026 alguien pidió un carrusel con
// cinco fotos de una carpeta de Drive y las cinco rebotaron: la primera con un
// 401 y las siguientes con «no es una imagen», que es literalmente cierto —lo
// que llegaba era HTML—. El agente terminó pidiéndole que las descargara y las
// volviera a subir a mano, que es el trabajo que esta herramienta existe para
// no hacer.
//
// Esta prueba sale a la red a propósito, y es la parte que importa: comprueba
// contra Drive DE VERDAD que las direcciones reescritas devuelven un JPEG. Una
// reescritura que parece correcta y no baja nada no sirve de nada, y eso sólo
// se ve preguntándole a Drive.
//
// También comprueba lo contrario: que una URL que no es de Drive se deje
// intacta, incluida `drive.google.com.loquesea.com`, que se parece y no es.

const src = await Deno.readTextFile("funciones/api-disenos/index.ts");
// Las dos funciones, sin las anotaciones de tipo: `new Function` evalúa
// JavaScript, no TypeScript. Se les sacan sólo a estas dos, que son cortas y
// las escribimos nosotros — no es un traductor, es un recorte.
const trozo = src.slice(src.indexOf("function idDeDrive"), src.indexOf("function direccion_valida"))
  .replace(/\(u: string\): string \| null/, "(u)")
  .replace(/\(u: string\): string\[\]/, "(u)")
  .replace(/\n  let url: URL;/, "\n  let url;");
const { idDeDrive, candidatas } = new Function(trozo + "\n return { idDeDrive, candidatas };")();

const ID = "1h79G5g1wI1I0yFutqQmKsXrkOYMphpW3";
let fallos = 0;
const ok = (c: unknown, q: string, d?: unknown) => {
  if (c) console.log("  ✓", q);
  else { fallos++; console.log("  ✗", q, JSON.stringify(d)); }
};

console.log("\n■ Reconoce las formas que usa Drive");
for (const u of [
  `https://drive.google.com/file/d/${ID}/view?usp=drivesdk`,
  `https://drive.google.com/open?id=${ID}`,
  `https://drive.google.com/uc?export=download&id=${ID}`,
  `https://docs.google.com/document/d/${ID}/edit`,
]) ok(idDeDrive(u) === ID, u.slice(0, 55) + "…", idDeDrive(u));

console.log("\n■ El id pelado, que es lo que el agente mandó la segunda vez");
{
  ok(idDeDrive(ID) === ID, "se reconoce sin URL", idDeDrive(ID));
  const c2 = candidatas(ID);
  ok(c2.length === 2 && c2[0].includes("uc?export=download"),
    "y sale la misma lista que con el link", c2);
}

console.log("\n■ Y NO toca lo que no es Drive");
for (const u of [
  "https://ndulchsiqutxibiwzzlc.supabase.co/storage/v1/object/public/disenos/x.jpg",
  "https://ejemplo.com/foto.jpg",
  "https://drive.google.com.malo.com/file/d/abcdefghij1234567890/view",
  // Un texto corto NO es un id: si lo fuera, cualquier palabra suelta se
  // convertiría en un pedido a Drive.
  "hola",
]) ok(idDeDrive(u) === null && candidatas(u).length === 1 && candidatas(u)[0] === u,
      "se deja igual: " + u.slice(0, 45) + "…", candidatas(u));

console.log("\n■ Las candidatas, en orden");
const c = candidatas(`https://drive.google.com/file/d/${ID}/view`);
ok(c.length === 2, "son dos", c.length);
ok(c[0].includes("uc?export=download"), "primero el archivo original", c[0]);
ok(c[1].includes("thumbnail"), "después el JPG que arma Drive", c[1]);

console.log("\n■ Y contra Drive de verdad");
for (const u of c) {
  const r = await fetch(u, { redirect: "follow" });
  const b = new Uint8Array(await r.arrayBuffer());
  const esJpg = b[0] === 0xFF && b[1] === 0xD8 && b[2] === 0xFF;
  ok(r.ok && esJpg, `${u.slice(0, 52)}… → JPEG de ${(b.length / 1024 | 0)} KB`,
     { http: r.status, tipo: r.headers.get("content-type") });
}
console.log(fallos ? `\n✗ ${fallos} fallo(s)\n` : "\n✓ todo bien\n");
Deno.exit(fallos ? 1 : 0);
