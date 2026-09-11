"""
Script de inicialización de datos.

Crea (si no existen) un usuario administrador del panel y un punto de
acceso por defecto, para poder probar la API de inmediato.

Uso (desde backend/, con el entorno virtual activado):

    python seed_db.py

Variables opcionales de entorno para el usuario administrador inicial:
    ADMIN_USUARIO   (por defecto: admin)
    ADMIN_PASSWORD  (por defecto: admin123, ¡cámbiala!)
"""
import os

from app import models, services
from app.database import Base, SessionLocal, engine


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin_usuario = os.getenv("ADMIN_USUARIO", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

        existente = (
            db.query(models.Usuario).filter(models.Usuario.usuario == admin_usuario).first()
        )
        if not existente:
            admin = models.Usuario(
                nombre="Administrador",
                usuario=admin_usuario,
                password_hash=services.hash_password(admin_password),
                rol=models.RolUsuario.ADMIN,
                estado=True,
            )
            db.add(admin)
            print(f"Usuario administrador creado: {admin_usuario} / {admin_password}")
        else:
            print(f"El usuario '{admin_usuario}' ya existe, no se crea de nuevo.")

        punto = db.query(models.PuntoAcceso).filter(models.PuntoAcceso.id == 1).first()
        if not punto:
            punto = models.PuntoAcceso(
                nombre="Entrada principal",
                ubicacion="Puerta principal del edificio",
                estado=True,
            )
            db.add(punto)
            print("Punto de acceso por defecto creado: 'Entrada principal'")
        else:
            print("Ya existe al menos un punto de acceso, no se crea de nuevo.")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
