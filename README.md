# Diseños automáticos — el estudio de plantillas

Proyecto para que un diseñador tenga un lugar donde **crear plantillas nuevas y
cambiar el diseño de las que hay**, sin tocar código y sin esperar un
despliegue. Hoy eso vive adentro del worker que corre en Google Cloud.

- **[docs/estudio-de-plantillas.md](docs/estudio-de-plantillas.md)** — el estudio donde un diseñador crea y edita plantillas sin desplegar. Empezá por acá.
- **[docs/el-disenador-vivo.md](docs/el-disenador-vivo.md)** — el estado verificado del tenant 119 y el bucle de correcciones del agente.
- **[prototipo/](prototipo/)** — la prueba corrida: una plantilla real fuera del
  código, con el PNG byte por byte idéntico.

## Contexto previo

Este proyecto continúa el sistema descrito en *«Traspaso del proyecto — Diseños
automáticos para clientes de Asistime»* (12/8/2026), que vive junto al resto de
la documentación en el proyecto de Claude **Boss Padel**:
`manual-del-sistema.md`, `como-funciona-en-asistime.md`,
`manual-de-marca-en-asistime.md`, `manual-que-se-escribe-solo.md`,
`que-construimos.md`, `estado-del-sistema.md`, `costo-por-diseno.md`.

## Lo urgente, que no cambió

La deuda de seguridad de la sección 10 del traspaso sigue abierta: tres claves
por rotar. Va antes que cualquier cosa de este repo.
