# Asistime.ai — identidad, de dónde sale cada dato

Lo que está acá salió de tres fuentes, en este orden de autoridad:

1. **Los archivos oficiales de logo** que pasó Joaquín (`Asisitme.ai_ logos/`).
   Los PNG de `logo/` son byte por byte esos archivos: no se redibujó nada.
2. **Las 28 piezas publicadas en @asistime.ai** al 10/8/2026. Los colores, la
   estructura del carrusel y la voz salen de mirarlas, no de un manual.
3. El kit `marca-asistime` del proyecto, que ya tenía la paleta medida.

Donde el manual histórico y las piezas publicadas no coinciden, **manda la
pieza publicada**: el manual listaba un Royal Blue `#3B82F6` y un violeta
`#8B5CF6` que la cuenta no usa.

## Color

| Rol | HEX |
|---|---|
| Azul de marca — logo, botones, burbujas de ícono | `#006AFF` |
| Azul de texto destacado sobre claro | `#005CFF` |
| Azul glow sobre fondo oscuro | `#2B8BFF` |
| Titular y texto sobre claro | `#00082F` |
| Texto secundario | `#3A4160` |
| Metadatos | `#7A8098` |
| Fondo base | `#FBFCFE` |
| Fondo oscuro | `#01030D` |
| Verde WhatsApp — **sólo** WhatsApp | `#25D366` |
| Rojo de alerta — **sólo** la plantilla `alerta` | `#F04438` |

Los dos fondos firma:

```
claro:  linear-gradient(155deg,#FDFDFF 0%,#F6F9FE 45%,#E9F0FE 100%)
oscuro: radial-gradient(120% 90% at 78% 62%,#062A6B 0%,#021340 38%,#01030D 78%)
```

**Asistime es clara por defecto.** Es la diferencia de registro más grande con
Boss Padel, que vive en negro. Acá el oscuro es la excepción y por eso pega.

## Tipografía

- **Sora** — titulares, números, botones, chips. Peso 800 con
  `letter-spacing:-.038em`. El aire compacto es parte del carácter.
- **DM Sans** — cuerpo, bajadas, texto de tarjetas. 400/500, 700 para destacar.

Están self-hosted en `fonts/` (woff2, subset latin) más cuatro TTF de peso fijo
para los rótulos de reel, porque freetype no entiende fuentes variables.

## Logo

`logo/` trae los seis archivos oficiales. **Nunca se recolorean a mano**: la
función `logo()` elige cuál de los tres isotipos usar según el fondo.

- El **isotipo** va arriba a la izquierda en toda placa, a ~62 px sobre 1080.
- El **lockup** completo se reserva para el cierre y la portada de un PDF.
- Nada de sombras, rotaciones ni deformaciones.

## Tony

Jirafa fotorrealista con anteojos redondos de marco negro y remera azul. Es la
cara del agente. El CTA canónico de la marca es **«Hablá con Tony»**.

Tony **no es el producto, es el ejemplo**: la línea correcta es *«En Asistime
lo llamamos Tony. El tuyo se puede llamar como quieras.»* El agente es del
cliente.

La imagen se **genera para cada pieza** siguiendo `assets/tony/tony-prompts.md`,
pasándole `assets/tony/tony-referencia.png` como referencia al modelo de imagen.
Un Tony repetido se nota en el feed.

## Voz

- Español rioplatense, voseo. «Hacés», «podés», «dejalo funcionando».
- Le hablás a un **dueño de pyme cansado**, no a un CTO. Nada de «LLM»,
  «orquestación», «workflow», «stack». Se dice *agente*, *responder mensajes*,
  *tarea programada*.
- Empezá por el dolor concreto, no por la tecnología.
- **Cuantificá.** Convertir la molestia en un número es lo que hace que la
  pieza funcione: 25 minutos por día → 12 horas por mes.
- Calmo y concreto. La marca vende tranquilidad; el tono tiene que sonar
  tranquilo. Nada de signos de exclamación en cadena.

**Evitar:** revolucionario, disruptivo, potenciá tu negocio, transformación
digital, «la IA llegó para quedarse», y emojis dentro de las piezas gráficas.
