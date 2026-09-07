# Cómo poner en producción — reels en video

Dos pasos. El de Supabase **ya lo hice yo** desde acá; te queda el de Cloud
Shell y el de Lovable.

---

## 1 · Supabase — ✅ ya está

Apliqué la columna `videos` a la tabla `disenos` y lo verifiqué. No tenés que
hacer nada. (Si alguna vez levantás el sistema de cero, `supabase.sql` ya la
trae.)

---

## 2 · Cloud Shell — redesplegar el worker

**Este despliegue es más importante que los anteriores**, porque el contenedor
cambió: sin esto los reels fallan aunque el código esté bien.

Lo que se agregó a la imagen:

- **ffmpeg** — el motor de los reels. No estaba.
- **fonts-noto-color-emoji** — sin esta fuente los emoticones de los rótulos
  salen como cuadraditos vacíos.
- **numpy** — la síntesis de los efectos de sonido.
- **requests** — se usaba pero venía de arrastre por otra dependencia, que es
  frágil. Ahora está declarado.

Subí el `worker.zip` nuevo por el menú de tres puntos de Cloud Shell y corré:

```bash
cd ~
rm -rf worker_viejo && [ -d worker ] && mv worker worker_viejo
unzip -q worker.zip && cd worker
export SUPABASE_URL="https://ndulchsiqutxibiwzzlc.supabase.co"
bash desplegar-chat.sh
```

Va a tardar más que otras veces: instalar ffmpeg engorda la imagen.

### Después del despliegue, comprobá que el contenedor quedó bien

```bash
gcloud run jobs execute boss-chat --region southamerica-east1 --wait
gcloud logging read \
  'resource.labels.job_name="boss-chat"' --limit 20 --format='value(textPayload)'
```

Si en los logs aparece `ffmpeg: not found` o un error de numpy, la imagen no se
reconstruyó — volvé a correr el despliegue.

---

## 3 · Lovable — el chip de Reel

Pegá `CAMBIOS-LOVABLE.md`. Suma el chip `Reel`, el reproductor de video en el
historial y el aviso de que un reel tarda más.

**Un detalle que importa:** ya existe un chip `Tapa de reel` cuyo valor es
`reel`, que da una **imagen fija** para portada. El chip nuevo vale `video` y
da el **mp4**. Son piezas distintas; el archivo se lo aclara a Lovable.

---

## Cómo verificar que quedó todo

En el chat, tres pedidos:

1. **Sólo `Cuadrado`** → una sola imagen. Verifica que los formatos se respetan.
2. **Sólo `Presentación PDF`** → tarjeta de descarga con un PDF de 6 a 9 páginas.
3. **Sólo `Reel`**, con «Un reel de cuenta regresiva para el torneo del 12 de
   setiembre, con jugadoras y ambiente del club» → un video vertical de unos
   12 segundos que se reproduce en el chat, **con sonido**.

En el tercero, mirá dos cosas: que los emoticones se vean (si salen cuadraditos
faltó la fuente en el contenedor) y que se escuchen los golpes en los cortes.

---

## Lo que cambió en el criterio, y no es técnico

Los reels ahora salen de **12 segundos y sin música**, y eso es a propósito:

- El estudio de Metricool sobre 24,3 millones de posteos da un tiempo promedio
  de visualización de **8,5 segundos**, con hasta la mitad de la gente
  abandonando antes del cuarto. Un reel de 20 segundos con el remate al final
  no lo ve casi nadie.
- La música va apagada porque Instagram restringe la biblioteca por tipo de
  cuenta, y porque pasar a cuenta de Creador desbloquea la app pero **no da
  licencia comercial**. El reel sale con el sonido de cancha y los efectos, y
  la música se le agrega en Instagram al publicar.

Todo el detalle, con fuentes, está en el documento «Audio y reels — tendencias»
del proyecto.
