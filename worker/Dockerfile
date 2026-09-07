FROM python:3.12-slim

# Chromium (motor de las placas y del PDF), ffmpeg (motor de los reels) y las
# fuentes. La de emoji es imprescindible: los rótulos de los reels llevan
# emoticones y sin ella salen como cuadraditos vacíos, que es peor que no
# ponerlos. Acá se ve bien porque el contenedor de desarrollo la trae; en
# Cloud Run hay que instalarla a mano.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
      fonts-noto-color-emoji \
      fontconfig libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
      libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
      libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium

# Precarga el modelo de transcripción. El contenedor es efímero: sin esto el
# modelo se baja de HuggingFace en CADA corrida. Con `large-v3` son 3,1 GB, y en
# Cloud Run el disco del contenedor ES MEMORIA, así que sin esta línea el job
# se queda sin memoria en vez de tardar un poco más.
#
# `HF_HOME` explícito no es adorno: sin él la caché queda en el $HOME del
# usuario que corrió el RUN, y si el job corre con otro usuario no la puede
# leer — se baja igual y no se entera nadie.
#
# Va ANTES de `COPY . .` a propósito: Docker invalida todas las capas que
# siguen a una que cambió, así que puesto después del código cada cambio de
# una línea de Python volvería a bajar 3,1 GB al construir la imagen.
ENV HF_HOME=/opt/modelos
RUN python -c "from faster_whisper import WhisperModel; \
      WhisperModel('large-v3', device='cpu', compute_type='int8')" \
    && chmod -R a+rX /opt/modelos

COPY . .
# Las tipografías de TODAS las marcas, no las de una. Cada marca vive en su
# carpeta bajo .claude/skills/ y trae las suyas; el glob evita tener que tocar
# el Dockerfile cada vez que entra un cliente nuevo.
RUN fc-cache -f /app/.claude/skills/*/fonts || true

# El comando real lo fija el despliegue (`--command python --args=-m,app.chat`).
# Este es el mismo, para que la imagen funcione sola si alguien la corre a mano.
CMD ["python", "-m", "app.chat"]
