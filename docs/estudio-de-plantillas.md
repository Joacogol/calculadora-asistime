# El estudio de plantillas

**Un lugar donde un diseñador crea plantillas nuevas y cambia el diseño de las
que hay, sin tocar código y sin esperar un despliegue.**

Escrito el 24 de agosto de 2026. Reemplaza la dirección del documento anterior
(`el-disenador-vivo.md`): ese apuntaba a entrenar el criterio del agente, y lo
que hace falta primero es esto. Lo que sigue valiendo de aquel documento es la
sección 00 —el estado verificado del tenant— y el bucle de correcciones.

---

## 1. Lo que encontré al abrir una plantilla

Fui a ver cómo es una plantilla de verdad, en el skill `boss-padel-disenos`.
El hallazgo cambia el tamaño del problema:

**Una plantilla ya es HTML y CSS.** Está envuelta en una función de Python que
la devuelve como f-string, y eso es lo único que la hace «código».

```python
def torneo(d, fmt="post"):
    h  = {"post": 1080, "vert": 1350, "story": 1920, "reel": 1920}[fmt]
    ac = C[d.get("acento", "lima")]
    inner = f"""
    <img class="bg" src="{d['foto']}">
    <div class="kicker" style="color:{ac};font-size:56px">{d['fecha_l1']}</div>
    ...
```

El motor no dibuja: **abre Chromium, carga ese HTML y le saca una foto**
(`render.py`, 34 líneas). O sea que el que sabe dibujar es el navegador, y la
plantilla es exactamente lo que un diseñador digital ya sabe leer.

La distancia entre «esto vive en el worker» y «esto lo edita un diseñador» es
mucho más corta de lo que parecía.

---

## 2. La prueba, corrida hoy

En vez de proponerlo, lo probé. Está en `prototipo/`.

Saqué la plantilla `torneo` del código y la dejé como dos archivos de datos:

```
plantillas/torneo/
├── plantilla.html    el diseño, con {{ campos }}
└── plantilla.json    el contrato: formatos, medidas y campos
```

Escribí un motor de 100 líneas que los interpreta y no sabe nada de ninguna
plantilla en particular. Rendericé los cuatro formatos con el motor de hoy y con
el nuevo, y comparé los PNG:

```
post   IDÉNTICO  c58931114a30eff4a1c417bd1cbcc7c2
vert   IDÉNTICO  c1c8f422d3b4b1d4f964b28fa197d4ff
story  IDÉNTICO  338e24ded9f8d18535186983a6daefc7
reel   IDÉNTICO  338e24ded9f8d18535186983a6daefc7
```

Byte por byte. **La plantilla salió del código sin cambiar un pixel.**

Después hice el segundo experimento: resolver el pedido que quedó pendiente
desde agosto —el renglón fijo al pie de las stories— editando sólo el archivo de
la plantilla. Tres líneas. Ningún archivo de código, ningún despliegue. Y el
post quedó con el mismo MD5 de antes: el cambio tocó sólo lo que tenía que
tocar. Está en `prototipo/comparacion-story.png`.

---

## 3. Qué es el estudio

Cuatro pantallas. Nada más.

### Galería
Las plantillas de la marca, cada una con su thumbnail renderizado de verdad y
sus formatos. Botones: **abrir**, **duplicar**, **nueva**.

### Editor
Dos paneles. A la izquierda el diseño; a la derecha el preview, y abajo los
campos con datos de ejemplo que el diseñador puede cambiar para ver casos
límite —un titular largo, una sede con nombre largo, sin foto—.

**El preview renderiza con el motor de producción.** Mismo Chromium, mismas
tipografías, mismo tamaño. Es la regla que no se negocia: cualquier preview que
dibuje de otra manera termina en «en el editor se veía bien».

### Campos
El contrato de la plantilla, editable como una lista: nombre, etiqueta, tipo
(texto, texto largo, imagen, opción, sí/no, lista), si es obligatorio, valor por
defecto. Es la pantalla más importante y explico por qué en la sección 5.

### Versiones
Borrador y publicada, con etiqueta y vuelta atrás. Igual que los documentos de
Asistime, que el equipo ya sabe usar. Publicar una plantilla es como publicar
una regla de marca: la pieza siguiente ya sale con el cambio.

---

## 4. Qué puede hacer un diseñador, en tres niveles

Vale ser honesto acá, porque «sin tocar código» significa cosas distintas según
el pedido.

### Nivel 1 · Cambiar lo que la plantilla ya expone — cero código
Los tokens de la marca (los colores `lima`, `naranja`, `negro`; las tipografías;
el logo) y los parámetros que la plantilla declara: tamaños, márgenes, posición
del logo, opacidad del degradado, si se muestra el salpicón.

Cambiar el token `lima` cambia las 14 plantillas de una. Esto cubre buena parte
de los pedidos reales que hoy llegan por `avisar_cambio_motor`.

### Nivel 2 · Editar el diseño de una plantilla — HTML y CSS con preview en vivo
Duplicar `torneo`, mover el titular, cambiar la grilla del pie, agregar un
bloque. Requiere leer HTML y CSS. Un diseñador digital lo tiene, o lo aprende en
una tarde con el preview al lado — que es la parte que lo hace enseñable: cambiás
un número y ves la pieza.

Este es el nivel donde el pedido de las stories se resolvió en tres líneas.

### Nivel 3 · Una plantilla nueva desde cero
Acá el camino corto no es escribir HTML en blanco: es **diseñar una pieza
concreta y convertirla en plantilla**. El diseñador arma el arte como lo armaría
siempre —en Figma, o en el canvas— con datos reales de un caso. Después, en el
estudio, marca qué partes son variables y eso genera el contrato de campos.

Es la misma operación que hace hoy un desarrollador cuando escribe la función,
pero al revés: en vez de imaginar los campos y después dibujar, dibujás y
después declarás qué se mueve.

---

## 5. El contrato: por qué la pantalla de campos es la más importante

`plantilla.json` declara cada campo con tipo, etiqueta y valor por defecto. De
esa única declaración salen **dos cosas al mismo tiempo**:

1. **El formulario** que ve el diseñador —y el que verá el club, si algún día se
   le da una pantalla para pedir piezas por plantilla—.
2. **El catálogo que lee el diseñador-IA.** Hoy el agente aprende las plantillas
   de un texto escrito a mano en el `SKILL.md`. Con el contrato declarado, el
   catálogo se genera solo:

```
- torneo — Placa insignia del club: foto de fondo, fecha en acento, TORNEO en
  tres líneas, sede y las tres columnas del pie.
  · Cuándo: anuncio de un torneo con fecha, sede y categorías.
  · Formatos: post, vert, story, reel
  · Campos: fecha_l1, fecha_l2, sede, cats_libres, cats_fem, contacto, foto,
    acento?, cta?, blob?, blob_color?
```

**Ese es el punto de todo esto.** Cuando el diseñador publica una plantilla
nueva, el agente la conoce en la pieza siguiente sin que nadie le explique nada,
y sin que nadie se acuerde de actualizar un texto en dos lugares. Es la misma
trampa del traspaso —un dato escrito a mano en dos lugares siempre termina
difiriendo— resuelta de raíz.

También desaparece uno de los errores de la lista: *«escribir en notas.txt que
una plantilla no existe sin haber leído la lista de plantillas»*. La lista deja
de ser algo que hay que acordarse de leer.

---

## 6. Qué cambia en el worker

Poco, y es la mejor noticia.

| Hoy | Después |
|---|---|
| `PLANTILLAS = {"torneo": torneo, ...}` en `templates.py` | el motor lee las plantillas publicadas de la marca |
| plantilla = función de Python | plantilla = HTML + contrato |
| agregar una plantilla = editar código y desplegar | agregar una plantilla = publicarla en el estudio |
| catálogo escrito a mano en `SKILL.md` | catálogo generado de los contratos |

El bucle de render no se toca. `motor/` —video, efectos, composición— no se
toca. El diseñador-IA no se toca: sigue eligiendo plantilla y llenando campos,
sólo que ahora la lista de plantillas viene de la base.

**Dónde se guardan.** En Supabase, en una tabla `plantillas` con marca, id,
html, contrato, versión y publicada. Es el mismo patrón que ya funciona con el
manual de marca: el worker las baja en cada corrida, cacheadas por versión, y
`metricas` registra con qué versión de cada plantilla se hizo la pieza. Si se
guardaran como archivos en el repo, seguiríamos necesitando desplegar — que es
justamente lo que se quiere sacar del medio.

---

## 7. Dónde vive el estudio

**Recomiendo que lo sirva el mismo worker**, como un servicio web chico al lado
del job que ya existe.

El motivo es uno solo y es el mismo de siempre: **el preview tiene que renderizar
con el motor de producción.** Mismas tipografías instaladas, mismo Chromium,
mismo tamaño de canvas. Si el estudio vive en otra app y dibuja el preview en el
browser del diseñador, se reimplementa el render y empieza la desincronización.
El worker ya tiene Chromium y las fuentes adentro de la imagen: es el único
lugar donde el preview y la pieza final no pueden diferir.

La pantalla puede ser Lovable si les resulta más rápido, siempre que el preview
sea una imagen que devuelve el worker y no un render del browser.

---

## 8. El plan

**Etapa 1 · Migrar las 14 plantillas al formato de datos.** 2 a 3 días.
Una por una, comparando el PNG contra el de hoy. La regla es la del prototipo:
si el MD5 no da igual, no está migrada. Las que tienen listas —`resultados`,
`agenda`, `promo`, `horarios`— necesitan un tipo de campo `lista` con columnas
declaradas; es lo único que falta escribir del motor.

**Etapa 2 · El motor lee de la base.** 2 a 3 días.
Tabla `plantillas`, lectura cacheada por versión, catálogo generado. Acá ya se
puede publicar una plantilla sin desplegar, aunque todavía se edite con un
editor de texto.

**Etapa 3 · El estudio.** 1 a 2 semanas.
Galería, editor con preview real, pantalla de campos, versiones.

**Etapa 4 · Los tokens de marca.** 3 días.
Colores, tipografías y logo salen de `brand.py` a la misma tabla. El nivel 1 de
la sección 4 pasa a existir.

**Etapa 5 · «Convertir en plantilla».** 1 semana.
Subir una pieza diseñada y marcar qué es variable. Es el nivel 3, y conviene
hacerlo último: recién con 14 plantillas migradas se sabe qué patrones se
repiten.

Antes de la etapa 1 sigue estando la rotación de las tres claves. No cambió.

---

## 9. Lo que no recomiendo

**Un editor visual propio, tipo Canva, con drag and drop.** Es un producto de
meses, compite con herramientas que el diseñador ya tiene y usa mejor, y el
resultado sería un editor peor que Figma que además hay que mantener. El valor
no está en dibujar adentro del estudio: está en que lo dibujado se convierta en
una plantilla que el agente sepa usar. Ese puente es la parte que no existe en
ningún lado y es lo que hay que construir.

---

## 10. Lo que hay que decidir

1. **¿El estudio es de Boss o es producto de Asistime?** Cambia dónde vive la
   tabla de plantillas y quién puede entrar. Si es producto, el estudio es una
   pantalla más de la plataforma y las plantillas son de la marca, no del repo.
2. **¿Quién es el diseñador?** No es lo mismo alguien que lee HTML —que arranca
   en el nivel 2 desde el día uno— que alguien que sólo trabaja en Figma, que
   necesita la etapa 5 antes de poder hacer nada solo.
3. **¿Repo nuevo?** `calculadora-asistime` está vacío y el nombre no dice nada
   de esto.

---

## Nota sobre lo que vi

El prototipo se corrió sobre el skill `boss-padel-disenos` que está sincronizado
en esta sesión: 6 plantillas. La producción tiene 14 y un `motor/` compartido que
no vi. La forma es la misma —función que devuelve HTML, Chromium que le saca una
foto— así que el resultado se sostiene, pero la estimación de la etapa 1 hay que
confirmarla con el repo del worker a la vista.
