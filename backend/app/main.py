"""
Punto de entrada de la aplicación FastAPI.

Para ejecutar en desarrollo (desde la carpeta backend/, con el
entorno virtual activado):

    uvicorn app.main:app --reload

La documentación interactiva queda disponible en /docs.
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (asegura que los modelos se registren en Base)
from app.config import validar_configuracion
from app.database import preparar_esquema
from app.programador import iniciar_programador_notificaciones
from app.routes import router

# En producción (APP_ENV=production) se niega a arrancar con la
# configuración de desarrollo (SECRET_KEY de ejemplo, CORS abierto...) --
# mejor que el servicio no levante a que quede "funcionando" inseguro.
validar_configuracion()

# Crea las tablas si no existen y agrega las columnas nuevas a las que ya
# existían (ver database.py). Es seguro con varios workers a la vez (usa un
# bloqueo de PostgreSQL). Para un proyecto en crecimiento se recomienda
# migrar a Alembic más adelante, pero esto es suficiente para el MVP.
preparar_esquema()

app = FastAPI(
    title="Sistema de Control de Acceso",
    description="API para el registro de entradas y salidas mediante código QR.",
    version="0.1.0",
)

# Orígenes permitidos para el panel React -- separados por coma en
# ALLOWED_ORIGINS (ver .env / .env.production.example). Sin esa variable
# (como en desarrollo local) se permite cualquier origen ("*"), para no
# complicar las pruebas locales del panel en distintos puertos.
_origenes_configurados = os.getenv("ALLOWED_ORIGINS", "").strip()
ALLOWED_ORIGINS = (
    [origen.strip() for origen in _origenes_configurados.split(",") if origen.strip()]
    if _origenes_configurados
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def _iniciar_tareas_en_segundo_plano():
    # Se guarda en app.state para que Python no la recolecte como basura
    # (asyncio no mantiene una referencia fuerte a las tareas por sí solo).
    app.state.tarea_notificaciones = iniciar_programador_notificaciones()


@app.get("/", tags=["healthcheck"])
def root():
    return {"status": "ok", "servicio": "control-acceso-backend"}
