"""
Configuración de la conexión a la base de datos (PostgreSQL) mediante SQLAlchemy.

La cadena de conexión se lee de la variable de entorno DATABASE_URL
(ver archivo .env.example). Si no está definida, se usa un valor por
defecto pensado solo para desarrollo local.
"""
import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/control_acceso",
)

# pool_pre_ping evita errores por conexiones "muertas" (útil si el
# backend corre por largo tiempo, como en un servicio permanente).
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: entrega una sesión de BD por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------------------------
# "Auto-migración" de columnas nuevas (mientras no haya Alembic)
# --------------------------------------------------------------------------
# `Base.metadata.create_all()` solo crea TABLAS que falten — si una tabla ya
# existía y el modelo le agrega columnas nuevas (como pasó con
# PuntoAcceso.ultimo_latido / comando_pendiente), esas columnas nunca se
# crean solas y cada consulta a esa tabla falla con un error de PostgreSQL
# ("column ... does not exist"), que en el navegador se ve como un genérico
# "Network Error" sin más detalle. Esto evita depender de que alguien se
# acuerde de correr el ALTER TABLE a mano: lo detecta y lo aplica solo al
# arrancar el backend. Es deliberadamente simple (agregar columnas
# nullable) — no reemplaza a Alembic para cambios más grandes.
COLUMNAS_NUEVAS = {
    "puntos_acceso": {
        "ultimo_latido": "TIMESTAMP NULL",
        "comando_pendiente": "VARCHAR(20) NULL",
        "mac_address": "VARCHAR(17) NULL",
    },
    "usuarios": {
        # DEFAULT TRUE también para usuarios que ya existían -- si un
        # admin se creó antes de este cambio, se le pide elegir su
        # propia contraseña la próxima vez que entre (mejora de
        # seguridad razonable, no debería sorprender a nadie en esta
        # etapa del proyecto).
        "debe_cambiar_password": "BOOLEAN NOT NULL DEFAULT TRUE",
    },
}


def asegurar_columnas_nuevas():
    inspector = inspect(engine)
    tablas_existentes = set(inspector.get_table_names())

    for tabla, columnas in COLUMNAS_NUEVAS.items():
        if tabla not in tablas_existentes:
            continue  # la tabla se acaba de crear con create_all: ya viene completa
        columnas_actuales = {c["name"] for c in inspector.get_columns(tabla)}
        faltantes = {nombre: tipo for nombre, tipo in columnas.items() if nombre not in columnas_actuales}
        if not faltantes:
            continue
        with engine.begin() as conexion:
            for nombre, tipo in faltantes.items():
                conexion.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}"))
                print(f"[auto-migración] Se agregó la columna {tabla}.{nombre}")


# --------------------------------------------------------------------------
# Arranque seguro con varios workers (producción usa `--workers 2`)
# --------------------------------------------------------------------------
# Con más de un worker de Uvicorn, todos importan `app.main` a la vez al
# arrancar (o al reiniciar el servicio en cada despliegue) y todos intentan
# crear las tablas y agregar las columnas nuevas al mismo tiempo. Sin
# coordinación, uno de los dos puede fallar con "relation already exists" /
# "column already exists" y el servicio queda caído justo después de un
# despliegue. Un bloqueo consultivo (advisory lock) de PostgreSQL hace que
# esos pasos se ejecuten de a un worker por vez -- el segundo espera, y al
# entrar ya encuentra todo creado. En otros motores (SQLite en pruebas) no
# hace nada.
CLAVE_BLOQUEO_ARRANQUE = 726001
CLAVE_BLOQUEO_NOTIFICACIONES = 726002


@contextmanager
def bloqueo_de_arranque():
    if engine.dialect.name != "postgresql":
        yield
        return
    with engine.connect() as conexion:
        conexion.execute(text("SELECT pg_advisory_lock(:clave)"), {"clave": CLAVE_BLOQUEO_ARRANQUE})
        try:
            yield
        finally:
            conexion.execute(
                text("SELECT pg_advisory_unlock(:clave)"), {"clave": CLAVE_BLOQUEO_ARRANQUE}
            )
            conexion.commit()


def bloquear_transaccion(db, clave: int) -> None:
    """Toma un bloqueo consultivo que se libera solo al terminar la
    transacción actual (commit/rollback/cierre de la sesión). Sirve para
    que dos workers no hagan a la vez un "revisar si existe y, si no,
    crear" (ver reportes.generar_notificacion_reporte_diario)."""
    if engine.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:clave)"), {"clave": clave})


def preparar_esquema() -> None:
    """Crea las tablas que falten y agrega las columnas nuevas, de forma
    segura aunque varios procesos arranquen al mismo tiempo."""
    from app import models  # noqa: F401  (registra los modelos en Base; import tardío para evitar ciclos)

    with bloqueo_de_arranque():
        Base.metadata.create_all(bind=engine)
        asegurar_columnas_nuevas()
