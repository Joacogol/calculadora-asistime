# Prototipo · la plantilla deja de ser código

Prueba de que una plantilla del motor puede salir del código sin cambiar un
pixel. Corrido y verificado el 24/8/2026 contra el skill `boss-padel-disenos`.

## Qué prueba

`templates.py` tiene la plantilla `torneo` como una función de Python que
devuelve HTML con f-strings. Acá está la misma plantilla como **dos archivos de
datos**:

- `plantillas/torneo/plantilla.html` — el diseño, con `{{ campos }}`
- `plantillas/torneo/plantilla.json` — el contrato: formatos, medidas y campos

`motor.py` los interpreta. No sabe nada de ninguna plantilla en particular:
agregar una es crear una carpeta.

**Resultado: PNG byte por byte idéntico en los cuatro formatos.**

```
post   IDÉNTICO  c58931114a30eff4a1c417bd1cbcc7c2
vert   IDÉNTICO  c1c8f422d3b4b1d4f964b28fa197d4ff
story  IDÉNTICO  338e24ded9f8d18535186983a6daefc7
reel   IDÉNTICO  338e24ded9f8d18535186983a6daefc7
```

## Cómo correrlo

Los archivos de acá van encima del skill, que aporta `brand.py`, las
tipografías, el logo y las fotos:

```bash
cp -r prototipo/* /ruta/al/skill/boss-padel-disenos/
cd /ruta/al/skill/boss-padel-disenos
pip install playwright jinja2

# el motor de hoy
python3 render.py ejemplo-spec.json

# el motor de plantillas-como-datos, con el mismo spec
python3 render_estudio.py ejemplo-spec.json
```

En este entorno Chromium está en `/opt/pw-browsers/chromium`; `render_estudio.py`
lo toma de ahí. En el worker de producción sale del `launch()` normal.

## El segundo experimento

El pedido que quedó pendiente desde agosto —el renglón fijo al pie de las
stories— se resolvió agregando **tres líneas a `plantilla.html`**, sin tocar un
archivo de código y sin desplegar:

```jinja
{% if fmt in ("story", "reel") %}
<div class="kicker" style="color:{{ ac }};font-size:32px;letter-spacing:.42em;text-align:center;margin-top:40px">#SOMOSPADEL</div>
{% endif %}
```

El post quedó con el mismo MD5 que antes: el cambio tocó sólo lo que tenía que
tocar. Ver `comparacion-story.png`.

## El contrato, y por qué importa

`plantilla.json` declara los campos con tipo, etiqueta y valor por defecto. De
ahí salen **dos cosas al mismo tiempo**:

1. El formulario que ve el diseñador en el estudio.
2. El catálogo que lee el diseñador-IA (`motor.catalogo()`).

Es el punto de todo esto: cuando alguien crea una plantilla, el agente la conoce
en la pieza siguiente, sin que nadie le explique nada.

## Lo que este prototipo NO resuelve

- Es una sola plantilla de las 14. Las que tienen listas (`resultados`,
  `agenda`, `promo`) necesitan un tipo de campo `lista` con columnas
  declaradas — Jinja lo soporta, falta escribirlo.
- No hay editor todavía: se edita el archivo con un editor de texto.
- `autoescape=False` replica el comportamiento de hoy. Cuando un dato venga de
  un pedido de chat hay que escaparlo y declarar los saltos de línea como un
  tipo de campo aparte.
- El video y los efectos siguen en `motor/`, sin tocar.

---

## Tercer experimento · una plantilla nueva, pedida

`plantillas/americano/` no salió de migrar nada: se creó de un pedido en
castellano —«una plantilla para americanos: día, hora, sede, precio por pareja
y cupos»— usando el sistema de diseño que ya está en el skill: los tokens de
`brand.py`, las clases de `base.css`, los helpers `logo()` y `aros()`, y las
plantillas que ya existen como referencia de oficio.

Salió on-brand a la primera. No porque generar diseño sea fácil, sino porque
**el vocabulario ya estaba escrito**: no hay que inventar una tipografía ni un
color, hay que componer con los que hay.

Un detalle que importa: el campo `precio_pareja` quedó **requerido**, con la
nota de por qué. Sale de la regla de marca del 12/8/2026 —«en todos los
anuncios de torneos siempre debe figurar el precio por pareja»—. La regla del
manual se convirtió en una restricción de la plantilla: ahora no se puede
generar la pieza sin el precio.

### Y después, la corrección

Tres notas de diseñador sobre la v1 —«no se ve la cancha», «el precio es lo que
más preguntan», «el bloque central flota»— se aplicaron como tres cambios en
`plantilla.html` y tres medidas en `plantilla.json`. Ver `CMP-americano.png`.

Eso es lo que hay que versionar: no la pieza, **la plantilla**. La v2 mejora
todas las piezas que se hagan de ahí en adelante.
