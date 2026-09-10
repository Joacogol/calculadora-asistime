# Larrique en Hetzner

Estado al 10/9/2026: diseños y edición de fotos de **Larrique General** (tenant 80, diseñador 605) funcionan en el servidor existente. Los pedidos y archivos siguen en el esquema `larrique` de Supabase; migrar alojamiento no sustituye los proveedores de IA ni sus costos.

## Código y ejecución

- `worker/Dockerfile.hetzner` construye desde este checkout completo, sin depender de una imagen antigua. La descarga de Whisper queda diferida y usa volumen persistente.
- `larrique.py` procesa como máximo un diseño y una foto nueva por ciclo; consulta también fotos asíncronas ya enviadas. No procesa otras marcas, vídeo ni publicación en redes.
- `asistime-larrique.timer` inicia otro ciclo aproximadamente un minuto después de terminar el anterior. Límite de 1,5 CPU, 4 GiB y 256 procesos. No expone puertos.
- `configurar_claves.py` y `configurar_fotos.py` solicitan claves con entrada oculta. Conservan el archivo privado `/opt/asistime-disenador/config/credenciales.json` con permisos 600. No poner valores en GitHub ni en mensajes.
- El contenedor de producción actual es `asistime-disenador:flujo-v5`. El instalador crea etiquetas basadas en el commit para despliegues futuros.

## Instalación o actualización

En el servidor, con un checkout limpio de la revisión que se desea instalar:

```bash
sudo bash deploy/hetzner/instalar.sh
```

Construye y prueba antes de cambiar el servicio. Si hay un ciclo activo, se detiene la instalación para no interrumpirlo. Conserva la configuración privada y una copia del runner y servicio anteriores. En una instalación nueva, cargar claves y activar el timer después:

```bash
python3 /opt/asistime-disenador/configurar_claves.py
python3 /opt/asistime-disenador/configurar_fotos.py
systemctl enable --now asistime-larrique.timer
```

Guardar Magnific habilita el procesamiento de fotos en el siguiente ciclo. El servicio deja las fotos pendientes mientras no esté configurada. Ante un error ambiguo del proveedor no vuelve a enviar automáticamente el pedido, para evitar duplicar cargos.

Comprobar `systemctl status asistime-larrique.timer`, `journalctl -u asistime-larrique.service` y el latido de Larrique en Supabase; verificar también el estado y URL del pedido. El log de limpieza puede mostrar «No such container» después de que Docker ya eliminó un contenedor exitoso.

## Plantilla de producto v3

`motor/encuadre_producto.py` mide el alfa de la foto y encaja la silueta manteniendo proporciones. Larrique define los márgenes respecto del encabezado, diagonal, lateral y pie. Story/reel reservan 250 px arriba y abajo. Las fotos opacas se conservan completas: no se inventa un recorte por color. Usar la foto resultante de quitar fondo cuando exista; el encuadre no elige por sí mismo otro archivo.

La plantilla incluye precio actual y precio anterior tachado. No depende de `foco_producto` para empujar la foto hacia abajo. Las pruebas cubren objetos altos, anchos, cuadrados, márgenes transparentes desplazados y fotos opacas; la carga de las seis marcas sigue comprobándose.

**Las plantillas publicadas de Supabase se sincronizan antes de cada diseño y pueden sobrescribir la copia del contenedor.** La versión 3 de `producto` ya está publicada y coincide con estos archivos. Un cambio futuro requiere actualizar tanto el código como la plantilla publicada, con respaldo, control de versión y lectura posterior. No basta con modificar sólo el HTML del repositorio. Antes de revertir a una imagen sin el ayudante de encuadre hay que restaurar la plantilla v2; de lo contrario fallará su render.

## Google y GitHub

El workflow `worker.yml` ejecuta pruebas; ya no autentica ni despliega a Google. Los scripts antiguos de Cloud Run permanecen como referencia, no deben usarse para actualizar Larrique. No se eliminaron los recursos de Google ni se reactivó su facturación. Antes de reactivarla deben revisarse los disparadores antiguos para evitar dos workers procesando las mismas colas.

Los cambios de este repositorio no se publican automáticamente en Hetzner. Instalar la revisión elegida con el procedimiento anterior y comprobar el resultado.


Actualización de calidad: el motor carga prioridades por marca desde `instrucciones_diseno` y el agente de Asistime resuelve primero la decisión de fondo. Ver `../asistime/README.md`. Imagen activa `flujo-v5`, que conserva el encuadre v3.

El acceso `worker/render.py --marca larrique-disenos spec.json salida` evita que el agente improvise lanzadores o intente escribir dentro de la carpeta protegida de skills. Se verificó con un render real sin red.

Prueba integrada del 10/9: el agente preguntó por el fondo antes de usar herramientas, reutilizó el recorte autorizado sin editarlo otra vez, y creó el pedido `d344de40-aec3-4787-9a9a-ac8e6bf069a0`. Terminó listo: producto completo, ambos precios, 25% OFF y sin marca agregada. La consulta de estado posterior usó `esperar=false`.
