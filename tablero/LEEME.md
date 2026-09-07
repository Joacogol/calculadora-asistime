# El tablero de administración

Una app estática: `index.html`, `app.js`, `estilo.css`. Lee el libro central
del Supabase de Asistime con la clave pública y una sesión de administrador
(email y contraseña; sólo los emails de `administradores` ven algo).

## Dónde vive

https://joacogol.github.io/calculadora-asistime/ — GitHub Pages, sirviendo la
raíz de la rama `main` de este repo. Los tres archivos de acá se copian tal
cual a la raíz de `main`.

**Por qué ahí y no en otro lado** (7/9/2026, medido, no supuesto):

- Vercel: el conector no tiene permiso para crear proyectos (403).
- Una función de borde de Supabase: la pasarela convierte todo `text/html`
  en `text/plain` con CSP de sandbox, a propósito.
- Supabase Storage: igual, el HTML sale como texto plano (antiphishing).
- Cloud Storage y Cloud Run: la organización de Google tiene «Domain
  restricted sharing» (`iam.allowedPolicyMemberDomains`) y no acepta
  `allUsers`; la excepción por proyecto no se pudo aplicar.
- Firebase Hosting: no se pudo agregar Firebase al proyecto.

GitHub Pages no pasa por ninguna de esas políticas. El repo es público; las
claves que van en `app.js` ya son públicas por diseño y los datos siguen
detrás del login.

## Cómo se actualiza

Desde la rama de trabajo, con los cambios ya commiteados:

```bash
git fetch origin main
git checkout main && git pull
cp tablero/index.html tablero/app.js tablero/estilo.css .
git add index.html app.js estilo.css && git commit -m "Tablero: …" && git push
git checkout -
```

Tarda un minuto en publicarse. `curl -sI https://joacogol.github.io/calculadora-asistime/app.js`
tiene que dar 200.

## El diseño

`worker/TABLERO-ADMIN.md`: qué mide, qué no, y las decisiones que quedaron.
