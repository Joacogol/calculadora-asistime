# Ducart Latin America — alta del 14/9/2026

Cliente operativo en Asistime, con registro de costos y sin descuento de saldo. Canal de atención autorizado: sólo Asistime. No WhatsApp.

## Identificadores verificados

- Tenant 189, slug `ducart`.
- Agente 625, Diseñador Ducart, activo y predeterminado. Modelo 100, temperatura 0.3, 12 pasos. Prompt publicado 5256.
- Agente vacío 624 desactivado, conservado sin eliminarlo.
- Documentos 911 (reglas), 912 (catálogo) y 913 (productos/fuentes), publicados y vinculados.
- Aplicación 61, clave 73: permisos exclusivamente de documentos de este tenant. Secreto en configuración privada, nunca en Git.
- 22 herramientas activas, IDs 2370–2391. Contratos sin claves en `deploy/ducart/tools.json`.
- Supabase compartido `qxjvtxumkljsroukpkny`, esquema `ducart`, bucket `disenos-ducart`, marca `ducart-disenos`, `cobra=false`.
- Clave exclusiva emitida por `alta_clave`, guardada en `/opt/asistime-disenador/config/ducart-alta.json`. Clave del worker en `ducart.json`, modo 600.

## Contenido

Seis plantillas publicadas y verificadas contra HTML y contrato: foto, producto, tecnico, jornada, cierre, rotulo. Post, vertical y story; carrusel, secuencia y PDF por composición del motor. Rótulo transparente para reel; música instrumental sintetizada del motor, `campo-calmo`.

17 fotos originales extraídas del folleto suministrado, subidas y verificadas por hash. Metadatos en `referencias/fotos.json`. El banco queda en Storage/DB; se conserva la exclusión histórica de `assets/banco/` en Git. Los logos y las fuentes sí viajan con la marca. El paquete completo de construcción está en el servidor y en la carpeta local de la marca.

Fuente: `/Users/joaquinrodriguez/Downloads/dla (2).zip`, su folleto de 21 páginas y revisión visual del perfil `https://www.instagram.com/ducartla/` y sus publicaciones. Mercoláctea 2025 y jornadas de agosto de 2026 son históricas. No se asumieron stock, precios, dosificaciones o teléfonos actuales. Colores medidos del logo: #134E2E, #D4D430, #7EAE57. Montserrat empaquetada; Avenir del folleto no fue suministrada como fuente completa.

## Despliegue

Imagen `asistime-disenador:ducart-v5`, derivada de `flujo-v5`. Servicio y timer `asistime-ducart`, cada 30 segundos tras finalizar el ciclo. Runner restringe explícitamente `config.clientes()` a Ducart. Incluye diseños, fotos, reels, plantillas, propuestas de motor y publicación autorizada. Las propuestas de motor no despliegan por sí solas. Otros servicios/clientes no fueron modificados.

SQL, en este orden: `ducart-disenos.sql`, `ducart-backend.sql`, `ducart-sin-prepago.sql`. El primero proviene del generador y tiene políticas restrictivas adicionales de membresía. El segundo concede funciones/secuencias al backend. El tercero deshabilita el prepago conservando vistas como `cuenta_interna` y `estado_prepago_interno`, accesibles sólo al backend. El motor/API existentes reconocen la ausencia de `mi_cuenta` como modo sin prepago. **No volver a aplicar sólo el primer SQL**: reintroduciría la vista de prepago. No se cargó saldo ficticio ni se borraron movimientos.

Corrección compartida en `app/fotero.py`: el resultado síncrono también llama al registro de costos, con los créditos/modelo recién obtenidos y la URL propia. La base `flujo-v5` y la copia local tenían hash idéntico antes de aplicar el cambio. Sólo se desplegó a Ducart; queda versionado para revisión antes de llevarlo a otros clientes.

## Pruebas y resultados

- 19 PNG iniciales: formatos de las seis plantillas y carrusel de 3 páginas, revisión visual.
- PDF de 4 páginas generado por motor, textos extraíbles y páginas revisadas.
- Secuencia de 3 stories y campos de precio/descuento probados con datos ficticios; el bloque comercial conserva contraste también sobre fondo claro.
- MP4 1080×1920 con rótulo y música: transparencia, dimensiones y pista de audio verificadas.
- Simulador Asistime conversación 258604: pedido real `2c9d1a03-5957-4606-9472-7d1c5c544a34`, listo y entregado por el agente con URL propia. USD 0.40344 registrados; precio al cliente 0, sin movimiento de cargo.
- Foto sin fondo `ea30cdb1-b8cd-492d-93d9-063c883f1a3e`, lista; 3 créditos Magnific registrados, precio 0. Registro inmediato recuperado una vez con `completar_registro.py`, luego leído y verificado.
- Prueba sin red de costos síncronos, asíncronos y pendientes, sin duplicación. Regresión `probar-crear-foto.py` aprobada.
- Las 22 herramientas fueron leídas individualmente tras crearlas; prompt, documentos y asociaciones verificados.
- Fallos detectados y resueltos antes de entregar: sintaxis Jinja/helper, URLs ausentes en banco (se agregan las 17 URLs comprobadas en la herramienta), vista de prepago activa por defecto, registro faltante de fotos síncronas.

## Límites actuales

Instagram no tiene cuenta conectada (`instagram_estado=[]`). La herramienta de publicación está instalada, exige autorización por pieza y no fue ejecutada. Habilitar publicación efectiva requiere OAuth/acceso a @ducartla. No se publicaron piezas.

Magnific está conectado y probado con edición real. fal.ai no está configurado y el prompt no lo ofrece como operativo. La generación paga de video no se disparó como prueba; sí se comprobó el montaje local con audio/rótulo. Plantillas/motor usan el modelo Sonnet 4.5 operativo. La conversión monetaria de créditos está sin configurar (`precio_credito_usd=null`), igual que Larrique: se guardan créditos reales, sin inventar su equivalencia en USD.

Muestras locales: `outputs/ducart/catalogo.html`, `outputs/ducart/pdf/catalogo-ducart.pdf`. Archivo fuente original del cliente y extracción: `outputs/ducart/fuentes/`. Los scripts en outputs son material de preparación, no la fuente autoritativa: usar la carpeta de marca y `deploy/ducart`.
