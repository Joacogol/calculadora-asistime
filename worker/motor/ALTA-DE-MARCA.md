# Dar de alta una marca nueva

Lo que hay que escribir para que un cliente nuevo tenga placas, carruseles,
secuencias de stories, reels, presentaciones PDF y efectos de clima.

**Lo que NO hay que escribir:** nada de eso. Chromium, ffmpeg, la síntesis de
sonido, los efectos, la numeración de un carrusel, la proporción única, las
zonas seguras de una story — todo eso ya está en `motor/` y lo hereda cualquier
marca el día que entra.

---

## La carpeta

```
.claude/skills/<marca>/
  SKILL.md            el manual: cuándo usar cada plantilla, qué no hacer
  marca.py            el enchufe — junta todo y lo expone como espera el motor
  brand.py            colores, formatos, logo vectorial, elementos gráficos
  templates.py        las plantillas de placa de esta marca
  diapositivas.py     cómo se ve cada diapositiva de un carrusel
  presentacion.py     los tipos de slide del PDF        (opcional)
  referencias/
    marca.md          reglas de color, tipografía y tono
    fotos.json        el banco catalogado
  assets/  fonts/  logo/
  render.py  video.py lanzadores de tres líneas, se copian tal cual
```

## El contrato

`marca.py` tiene que exponer:

| | |
|---|---|
| `C` | dict de colores |
| `FORMATOS` | dict formato → (ancho, alto) |
| `BASE_CSS` | la hoja de estilo base |
| `PLANTILLAS` | dict nombre → función(data, formato) → HTML |
| `logo(size, color, align)` | el logo como HTML |

Y, si la marca quiere carruseles:

| | |
|---|---|
| `DIAPOS` | dict tipo → función(data, ancho, alto, acento) → cuerpo HTML |

`portada` y `cierre` son obligatorios —un carrusel siempre abre y cierra igual—
y `cuadro` hace falta para secuencias de stories. Los del medio los define cada
marca según lo que publique.

`motor.contrato.verificar()` corre solo y falla con nombre y apellido si falta
algo. Es la diferencia entre «la marca nueva no anda» y «falta `PLANTILLAS`».

---

## El orden importa

Los pasos están en este orden porque cada uno depende del anterior, y saltarse
el tercero es el error que más caro sale.

### 1 · Sacar la identidad real, no la que dicen que tienen

Del material que exista: piezas anteriores, el logo original en vector, el
manual si lo hay. Colores en HEX exactos, no aproximados. Tipografías reales,
en TTF de peso fijo — una fuente variable como Archivo la renderiza ffmpeg
siempre en regular, así que para los rótulos de reel hace falta un peso fijo.

Esto va a `referencias/marca.md` y a `brand.py`.

### 2 · Dos o tres plantillas, no nueve

Boss Padel tiene nueve porque se fueron sumando con el uso. Una marca nueva
arranca con las que va a usar la primera semana. Agregar una plantilla después
cuesta una hora; mantener seis que nadie usa cuesta para siempre.

### 3 · Catalogar el banco de fotos — y mirarlo

`referencias/fotos.json` lleva, por foto: qué se ve, para qué sirve, **quién
aparece** (género, cantidad, edad, apariencia) y el **punto focal ya resuelto
para cada formato**.

Es el paso más laborioso y el que más rinde. Sin `quien`, un pedido como «con
jugadoras» o «que no sea rubio» hace que el agente busque hasta quedarse sin
turnos y termine sin entregar nada — pasó, costó 339 segundos y salió error.
Sin `foco` precalculado, la misma foto sale encuadrada distinto en cada corrida
y a veces la cara choca con el titular.

**Y hay que mirar las fotos, no leer los nombres de archivo.** En Boss Padel
cuatro clips que parecían de juego eran el perro del club y gente sentada en el
lounge, y cuatro imágenes catalogadas como «fondos neutros» eran rectángulos
casi negros. Las dos cosas se descubrieron armando una hoja de contacto y
mirándola. `herramientas/hojas.py` la arma.

### 4 · Escribir el SKILL.md como un manual, no como una lista

Lo que más valor tiene no es qué plantillas hay: es **qué no hacer y por qué**.
Cada regla del SKILL.md de Boss Padel salió de una pieza que salió mal. Una
marca nueva no tiene ese historial todavía, así que arranca con lo genérico y
se le van sumando las suyas.

### 5 · Renderizar y mirar antes de darlo por bueno

Todos los defectos serios de este sistema se encontraron mirando, no
compilando: el índice del carrusel pisando el texto, el «CONTACTANOS AL» sin
número, las gotas de lluvia que parecían rayones, el reel que en Mac mostraba
un cuadro congelado. Ninguno daba error.

---

## Lo que se hereda gratis

Para que quede dimensionado lo que **no** hay que rehacer:

- Chromium renderizando placas, carruseles y PDF con la misma tipografía
- ffmpeg armando reels verticales, con la uniformidad de codificación que evita
  que se vean congelados en Mac
- Sonido sintetizado — sin descargas ni licencias
- Cinco efectos de clima en CSS y SVG
- La estructura del carrusel: numeración, proporción única, índice, flechas
- Las zonas seguras de story y la caja de respuesta
- El worker, la cola, la subida a Storage y las métricas de costo

## El color de acento encima de una foto — vale para TODAS las marcas

Es la regla que más veces nos mordió, en las dos marcas, y por eso vive en el
motor y no en el skill de nadie.

**Un color de acento de luminancia media no se lee como texto sobre una foto.**
Medido en tres stories publicables de Clínica Preventiva, con la palabra
destacada en el rojo de la marca:

| Sobre qué | Contraste |
|---|---|
| El mostrador de la recepción | **1,72 : 1** |
| La cara de una persona | **1,43 : 1** |
| Una túnica blanca | **1,02 : 1** |

El mínimo para texto grande es 3,0:1. En la tercera el rojo tenía literalmente
la misma luminancia que la túnica: la palabra no estaba.

**Y no se arregla con más velo.** El techo teórico de ese rojo es 5,05:1 contra
negro PURO. Para acercarse habría que tapar la foto entera, y entonces no tiene
sentido haber puesto la foto.

### La salida es de diseño, no de tipografía

Cuando el acento no llega como texto, **la palabra va adentro de un bloque
sólido del color de acento**. El blanco sobre el rojo de marca da 4,16:1 pase
lo que pase debajo, porque ya no depende de la foto. Y la firma de la marca
—la palabra que importa, en el color de acento— se conserva: cambia de ser
tinta a ser fondo.

### Cómo se usa

`motor/legibilidad.plan_titular(foto, acento, oscuro)` devuelve:

```python
{"velo": 0.46, "modo": "bloque", "contraste": 1.91, "tinta": "#FFFFFF"}
```

- `velo` — cuánto oscurecer la foto para que el texto BLANCO se lea. Es un
  piso, no un reemplazo del criterio de diseño: si tu plantilla necesita 0,52
  para que las mitades se lean como bloques, usá `max(0.52, velo)`.
- `modo` — `"texto"` o `"bloque"`.
- `tinta` — de qué color va el texto adentro del bloque. Un acento claro
  —un lima, un amarillo— pide tinta oscura; uno medio u oscuro pide blanco.
  Lo decide el motor, no la marca.

Sin foto, o si el archivo no se puede abrir, devuelve `bloque`: ante la duda
vale más una pieza legible que una linda.

**Ninguna plantilla nueva con texto sobre foto se da por terminada sin llamar a
esto.** No inventes un degradé a ojo ni elijas el modo por gusto: la misma
plantilla recibe fotos de día y de noche, y una decisión fija se rompe con la
primera foto que no viste.
