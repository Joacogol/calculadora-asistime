# Diseñador Larrique en Asistime

Tenant 80, agente 605. Prompt publicado: versión 6, ID 5109 (10/9/2026), ver `larrique-prompt.md`. Se respaldó la versión 4 (ID 5039) antes de crear la nueva; publicar se confirmó leyendo currentPromptVersionId del agente.

El flujo resuelve fondo antes de encargar la placa, consulta cuando no hay una decisión y reutiliza el recorte de la misma foto cuando ya existe. Espera la edición antes de diseñar y pasa sólo la URL final. Si la marca no está confirmada, no añade nombre ni logo. El brief conserva precios y porcentaje; los beneficios no se inventan.

La configuración de Asistime y la del worker son dos capas distintas: cambiar una no publica la otra. Las prioridades del worker están en `worker/.claude/skills/larrique-disenos/marca.json`, campo `instrucciones_diseno`, que se antepone al prompt de cada generación. Las marcas sin ese campo siguen igual.

Prueba conversacional en simulador 247433: ante foto blanca y marca desconocida preguntó por quitar fondo y no llamó herramientas hasta recibir la decisión. Segunda parte: se indicó el recorte existente para verificar que cree la placa sin otra edición de foto. No confundir una prueba de preguntas con garantía de comportamiento universal del modelo.

La versión 6 consulta estado_diseno con esperar=false para evitar esperas de 55 segundos dentro del stream del chat. Durante la prueba, esperar=true completó en el servidor, pero el navegador mostró error; los mensajes quedaron guardados y el pedido siguió generándose.
