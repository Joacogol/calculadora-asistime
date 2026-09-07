# Tony — generación de imagen por pieza

Tony **no es un sticker fijo**. Se genera una imagen nueva para cada pieza, adaptada a lo que dice
esa pieza. Si Tony aparece siempre en la misma pose, el feed se lee repetido.

La imagen se genera **con una IA de imagen** (Nano Banana / Gemini, ChatGPT / GPT Image, Midjourney,
Firefly — la que uses). Este archivo te da la ficha del personaje, el prompt base y las variantes.

---

## 1. Ficha del personaje — esto NO cambia nunca

Copiá este bloque en todos los prompts. Es lo que mantiene a Tony reconocible entre piezas.

> A photorealistic anthropomorphic giraffe character named Tony. Distinctive features that must stay
> identical in every image: **large round black-rimmed glasses**, warm brown-and-cream giraffe pattern,
> gentle friendly expression, calm and competent — never goofy or cartoonish. He wears either a
> **royal blue crew-neck t-shirt** or a **black zip hoodie**. Photorealistic rendering, soft natural
> lighting, shallow depth of field, professional photography look.

**Referencia visual:** pasale `tony-referencia.png` como imagen de entrada al modelo. Los modelos que
aceptan referencia (Nano Banana, GPT Image, Midjourney con `--cref`) mantienen mucho mejor la cara si
le das la imagen además del texto. Es la diferencia entre "una jirafa con anteojos" y **Tony**.

**Nunca:** Tony sin anteojos · estilo caricatura plana o 3D tipo Pixar · otro animal · expresión
agresiva o burlona · Tony haciendo algo que el copy no dice.

---

## 2. Prompt base

```
[FICHA DEL PERSONAJE]

Scene: {{QUÉ ESTÁ HACIENDO TONY}}.
Setting: {{DÓNDE}}.
Composition: {{ENCUADRE}}, subject positioned on the {{right/left}} side of the frame,
  large empty area on the opposite side for text overlay.
Lighting: soft, bright, clean. Cool blue ambient accents (#006AFF).
Style: photorealistic, professional, uncluttered. No text, no logos, no watermarks in the image.
Aspect ratio: 4:5.
```

Dos reglas que hacen la diferencia:

- **Pedí siempre el espacio vacío** para el texto (`large empty area…`). Si no, sale Tony centrado y
  el titular no tiene dónde ir.
- **Pedí que no genere texto ni logos.** Los modelos escriben "Asistime" mal. El logo lo pone el
  template, no la IA.

---

## 3. Variantes por rol de slide

| Rol de la pieza | `Scene` sugerido | Ropa |
|---|---|---|
| **Solución / alternativa** | *working calmly at a laptop in a bright modern office, hands on the keyboard, focused and relaxed* | remera azul |
| **Cierre / CTA** | *standing with arms crossed, looking at the camera with a confident friendly smile* | buzo negro |
| **Atención al cliente** | *sitting across a wooden table from a human client, mid-conversation, attentive* | remera azul |
| **Pensando / pregunta** | *one hoof thoughtfully at his chin, looking slightly upward, curious expression* | buzo negro |
| **Nocturno / 24-7** | *working at a desk at night, screen glow on his face, calm* | buzo negro |
| **Celebración / resultado** | *leaning back in an office chair, relaxed, coffee mug in hand* | remera azul |

Para el **slide oscuro de impacto**, si va Tony: agregá
`dark background, dramatic blue rim lighting, low key` y bajá la presencia — ese slide es del número,
no del personaje.

---

## 4. Después de generar

1. **Recortá el fondo** (fondo transparente). Si el modelo no lo da, pedí
   `isolated on a plain white background, clean edges` y recortá después.
2. **Chequeá los anteojos.** Es lo primero que los modelos deforman. Si salieron ovalados, torcidos o
   con una sola patilla, regenerá — no lo dejes pasar, es el rasgo que hace a Tony.
3. **Chequeá las manos/pezuñas.** El segundo error más común.
4. **Guardá la buena** en `assets/tony/` con nombre descriptivo (`tony-laptop-noche.png`). Las que
   funcionan se acumulan y con el tiempo tenés banco propio.

---

## 5. Cómo se monta en el template

En `template-carrusel.html` los slides 5 y 6 traen un slot:

```html
<div class="tony-slot">TONY VA ACÁ<small>ver tony-prompts.md</small></div>
```

Cuando tenés el PNG, reemplazalo por:

```html
<img class="tony" src="tony/tony-laptop-noche.png" alt="Tony">
```

La clase `.tony` ya tiene posición, tamaño y sombra resueltos. Ajustá `height` y `right` si la pose
lo pide.
