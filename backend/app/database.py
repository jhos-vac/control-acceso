"""
Configuración de la conexión a la base de datos (PostgreSQL) mediante SQLAlchemy.

La cadena de conexión se lee de la variable de entorno DATABASE_URL
(ver archivo .env.example). Si no está definida, se usa un valor por
defecto pensado solo para desarrollo local.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
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
