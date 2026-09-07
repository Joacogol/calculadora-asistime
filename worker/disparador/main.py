# -*- coding: utf-8 -*-
"""Disparador — convierte un pedido nuevo en una corrida del worker.

Supabase llama a este servicio en el mismo momento en que se inserta la fila
en `disenos`. El servicio arranca el Cloud Run Job y contesta enseguida: no
espera a que el diseño termine.

Por qué existe un servicio en el medio en vez de que Supabase llame al Job
directamente: la API de Cloud Run pide autenticación de Google, y este
servicio ya corre *como* la cuenta de servicio, así que la obtiene del entorno
sin ninguna clave. Supabase sólo necesita un secreto compartido.

Es minúsculo y escala a cero: se paga por milisegundo de request, no por hora.
"""
import hmac
import logging
import os

import google.auth
import google.auth.transport.requests
import requests
from fastapi import FastAPI, Header, HTTPException, Response

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("disparador")

PROYECTO = os.environ["PROYECTO"]
REGION = os.environ.get("REGION", "southamerica-east1")
JOB = os.environ.get("JOB", "boss-chat")
SECRETO = os.environ["SECRETO"]

URL_RUN = (f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/"
           f"namespaces/{PROYECTO}/jobs/{JOB}:run")

app = FastAPI()
_creds = None


def _token() -> str:
    """Token del entorno. Sin archivos de credenciales."""
    global _creds
    if _creds is None:
        _creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not _creds.valid:
        _creds.refresh(google.auth.transport.requests.Request())
    return _creds.token


@app.get("/")
def salud():
    return {"ok": True, "job": JOB, "region": REGION}


@app.post("/disparar")
def disparar(x_secreto: str = Header(default="")):
    # compare_digest evita filtrar el secreto por diferencias de tiempo
    if not hmac.compare_digest(x_secreto, SECRETO):
        log.warning("llamada rechazada: secreto incorrecto")
        raise HTTPException(status_code=401, detail="no autorizado")

    r = requests.post(URL_RUN,
                      headers={"Authorization": f"Bearer {_token()}"},
                      timeout=20)

    # 409 = ya hay una ejecución en curso. No es un error: el worker que está
    # corriendo va a levantar este pedido también, porque lee todos los
    # pendientes de una.
    if r.status_code == 409:
        log.info("ya hay una corrida en curso; el pedido entra en esa")
        return Response(status_code=202)

    if not r.ok:
        log.error("no se pudo arrancar el job: %s %s", r.status_code, r.text[:300])
        raise HTTPException(status_code=502, detail="no se pudo arrancar el job")

    log.info("job arrancado")
    return Response(status_code=202)
