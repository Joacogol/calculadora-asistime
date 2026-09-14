# Ducart

Configuración exclusiva del cliente 189 / agente 625. Ver `docs/ducart-alta-2026-09-14.md` para evidencias, límites y orden de migraciones.

`runner.py` ejecuta el motor compartido únicamente para `ducart-disenos`. `Dockerfile` usa `flujo-v5` y añade la marca y la corrección de costos síncronos. Contexto de construcción: carpeta con `.claude/skills/ducart-disenos`, `app/fotero.py` y Dockerfile. Los archivos de banco se recuperan de Storage; no están versionados.

`alta_base.py` se ejecuta sólo en el servidor, usando sus credenciales existentes. Guarda claves en configuración privada. `sembrar.py` publica plantillas y carga el banco con lectura posterior y verificación de bytes. No ejecutar sin haber preparado los assets del cliente.

`preparar_tools.py` produce contratos con marcadores, nunca claves. Sustituir `__DUCART_API_KEY__` y `__ASISTIME_DUCART_KEY__` únicamente en memoria al crear/actualizar herramientas de Asistime. No publicar contratos sin sustituir ni guardar variantes con secretos.

`probar_api.py` es idempotente en esta instalación: crea como máximo una foto de prueba y consulta el diseño de prueba registrado. `completar_registro.py` recupera sólo el registro de esa foto ya existente y exige `cobra=false`. No regenera ni cobra.

Pruebas sin red en el contenedor:

- `herramientas/probar-costo-foto-sync.py`
- `herramientas/probar-crear-foto.py`
- `probar_medios.py` con `/revision` montado para la muestra MP4; fuente de música empaquetada.

Nunca copiar `config/ducart.json`, `config/ducart-alta.json` ni `credenciales.json` al repositorio o al contexto Docker. Para activar una nueva imagen, actualizar sólo el servicio `asistime-ducart`, leer su configuración efectiva y verificar el próximo ciclo.
