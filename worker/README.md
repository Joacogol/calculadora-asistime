# Chat de diseños — Boss Padel

La persona pide un diseño por el chat de Lovable y la pieza aparece ahí mismo,
lista para descargar.

```
Lovable  →  insert en `disenos`  →  webhook  →  disparador  →  Cloud Run Job
                                                                    ↓
Lovable  ←──────── Realtime ────────  Supabase Storage  ←──── piezas + copy
```

## Las partes

| Archivo | Qué hace |
|---|---|
| `app/chat.py` | El ciclo: toma los pendientes, diseña, sube, marca listo |
| `app/supa.py` | Lee la tabla `disenos` y sube a Storage |
| `app/disenador.py` | Le pasa el pedido al Agent SDK con el skill cargado |
| `app/config.py` | Teléfonos y colores por sede, y el entorno |
| `disparador/` | Servicio mínimo que Supabase llama al insertar |
| `.claude/skills/boss-padel-disenos/` | 9 plantillas, fuentes, logo, banco de fotos |

## El candado

`supa.tomar()` hace un `UPDATE ... WHERE estado = 'pendiente'` y mira si afectó
alguna fila. La condición y la escritura ocurren en la misma operación, así que
si dos corridas se solapan sólo una se queda con el pedido. Postgres lo
garantiza; no hace falta nada más.

## Puesta en marcha

1. Aplicar `supabase.sql` en el proyecto (ya está hecho en Boss Padel).
2. `bash desplegar-chat.sh` — pide la service_role key una sola vez.
3. `bash desplegar-disparador.sh` — imprime la URL y el secreto para el webhook.
4. Pegar `PROMPT-LOVABLE.md` en Lovable.

## Autenticación sin claves

El worker no usa ningún archivo de credenciales de Google: en Cloud Run corre
*como* la cuenta de servicio. La única credencial que maneja es la service_role
de Supabase, que vive en Secret Manager y nunca toca el frontend.
