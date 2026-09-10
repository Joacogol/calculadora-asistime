# Clínica Preventiva — estado 10/9/2026

Tenant73, diseñador542. Manual833 publicado en versión1, ID1645; contenido leído de vuelta y verificado. El motor en Hetzner pudo leerlo con la clave de la aplicación34, guardada privadamente en config/clinica.json (nunca en el repositorio).

Prompt del diseñador publicado en ID5123, sustituyendo ID4776. Tool estado_diseno2064 actualizada y releída: una sola petición con esperar=no, sin espera larga ni bucles. Prueba de respuesta generando: devuelve éxito, listo=false, mismo id. El código versionado contiene marcador de clave, no la clave productiva. No reemplazar el código vivo por el marcador.

Servicio de Clínica activo con imagen compartida flujo-v5, base jejohzzxxnhktdxpdqpy, bucket disenos. Procesa una pieza y una edición de foto nuevas por ciclo; no publica en Instagram ni procesa reels/plantillas. No se modificó la atención a pacientes ni el servicio de Larrique.

## Activación
Clave de Supabase cargada por Joaquín y verificada por lectura (HTTP200). No había diseños pendientes ni generando antes de activar. Servicio instalado, primer ciclo success, temporizador habilitado y activo.

Prueba integrada en conversación248779: Asistime consultó ver_banco y creó story c9917696-e6b1-4b2b-8924-0843b525983e y post 28d2474a-d278-4565-b1cd-107fca1b5f1a. El worker sincronizó 20 fotos, 4 plantillas publicadas y leyó manual v1. Ambos diseños terminaron listos y se revisaron visualmente: foto real del banco, anuncio solicitado y ambas direcciones, sin horarios inventados. Feed listo 18:19 UTC; story lista 18:22 UTC. La consulta durante procesamiento devolvió estado inmediatamente; la consulta final entregó los enlaces correctos de ambos pedidos, sin generar pedidos adicionales.

Cambios de configuración subidos en commit 2cacdc7; CI Worker (ejecución 34513035873) exitosa. PUBLICAR=0: esta verificación cubre generación y entrega, no publicación en Instagram. El agente todavía ofrece publicación en su respuesta; esa capacidad no quedó validada ni activada en este servicio.
