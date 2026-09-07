#!/usr/bin/env bash
# Despliega el disparador y te deja la URL y el secreto para pegar en Supabase.
set -euo pipefail

PROYECTO="boss-padel-disenos"
REGION="southamerica-east1"
SA="worker-boss-padel@${PROYECTO}.iam.gserviceaccount.com"

# Secreto compartido con Supabase. Se genera una vez y se guarda.
if ! gcloud secrets describe disparador-secreto --quiet >/dev/null 2>&1; then
  openssl rand -hex 32 | gcloud secrets create disparador-secreto --data-file=- --quiet
fi
SECRETO=$(gcloud secrets versions access latest --secret=disparador-secreto)

gcloud run deploy boss-disparador \
  --source ./disparador \
  --region "$REGION" \
  --service-account "$SA" \
  --allow-unauthenticated \
  --memory 512Mi --cpu 1 --max-instances 3 --timeout 30s \
  --set-env-vars "PROYECTO=${PROYECTO},REGION=${REGION},JOB=boss-chat,SECRETO=${SECRETO}" \
  --quiet

# Permiso para arrancar el job
gcloud run jobs add-iam-policy-binding boss-chat --region "$REGION" \
  --member="serviceAccount:${SA}" --role="roles/run.invoker" --quiet

URL=$(gcloud run services describe boss-disparador --region "$REGION" --format='value(status.url)')

cat <<FIN

════════════════════════════════════════════════════════════
  PEGÁ ESTO EN SUPABASE
  Database → Webhooks → Create a new hook
════════════════════════════════════════════════════════════

  Nombre    : disparar-diseno
  Tabla     : public.disenos
  Eventos   : INSERT
  Tipo      : HTTP Request
  Método    : POST
  URL       : ${URL}/disparar

  Headers   :
    x-secreto: ${SECRETO}

════════════════════════════════════════════════════════════
FIN
