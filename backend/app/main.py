"""
Punto de entrada de la aplicación FastAPI.

Para ejecutar en desarrollo (desde la carpeta backend/, con el
entorno virtual activado):

    uvicorn app.main:app --reload

La documentación interactiva queda disponible en /docs.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (asegura que los modelos se registren en Base)
from app.database import Base, engine
from app.routes import router

# Crea las tablas si no existen. Para un proyecto en crecimiento se
# recomienda migrar a Alembic más adelante, pero esto es suficiente
# para el MVP.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Control de Acceso",
    description="API para el registro de entradas y salidas mediante código QR.",
    version="0.1.0",
)

# En producción, restringir allow_origins al dominio real del panel React.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["healthcheck"])
def root():
    return {"status": "ok", "servicio": "control-acceso-backend"}
