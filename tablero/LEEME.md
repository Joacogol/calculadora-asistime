# El tablero de administración

Una página estática (`index.html`, `app.js`, `estilo.css`) que lee el libro
central del Supabase de Asistime. Sin build, sin dependencias: `supabase-js`
viene del CDN. Entra con un enlace por email; la base sólo le contesta a los
emails que están en la tabla `administradores`.

## Dónde vive

En un bucket público de Google Cloud Storage del proyecto `boss-padel-disenos`,
que ya es donde corre el worker:

    https://storage.googleapis.com/boss-padel-disenos-tablero/index.html

Se probaron dos lugares antes y los dos están descartados por razones que no
van a cambiar: el conector de Vercel no puede crear proyectos (403), y una
función de borde de Supabase **no puede servir HTML** — la pasarela reescribe
`text/html` como `text/plain` y le pone `Content-Security-Policy: sandbox`,
a propósito, para que nadie aloje páginas en `supabase.co`.

## Publicarlo o actualizarlo

Desde Cloud Shell, parado en el clon del repo:

```bash
gsutil -m -h "Cache-Control:no-cache" cp tablero/index.html tablero/app.js tablero/estilo.css \
  gs://boss-padel-disenos-tablero/
```

La primera vez, antes de eso:

```bash
gsutil mb -p boss-padel-disenos -l southamerica-east1 gs://boss-padel-disenos-tablero
gsutil iam ch allUsers:objectViewer gs://boss-padel-disenos-tablero
```

Y en Supabase (proyecto `qxjvtxumkljsroukpkny`, Authentication → URL
Configuration) la URL de arriba tiene que estar como **Site URL** y en
**Redirect URLs**: si no, el enlace del email manda a `localhost:3000`.

## Probarlo sin base

`herramientas/probar-tablero` no existe: la prueba es abrir `index.html` con
un `supabase.createClient` de mentira, como se hizo el 7/9/2026 con Playwright
(ocho pantallas, cero errores de JS). Si se toca `app.js`, repetir eso antes
de subirlo.
