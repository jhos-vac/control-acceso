"""
Recuperar el acceso al panel cuando NADIE puede entrar (se perdió u
olvidó la contraseña del único ADMIN, así que no hay forma de usar el
reseteo desde el propio panel -- POST /api/usuarios/{id}/resetear-password
requiere justamente ser un ADMIN ya logueado).

Este script se corre DIRECTO en el servidor donde vive la base de datos
(no llama a la API) -- por eso no hace falta ningún login, configurar
correo, ni nada más que acceso a la máquina y a `DATABASE_URL` (el mismo
`.env` que usa el backend). Es el mismo enfoque que ya usa `seed_db.py`.

Uso (desde backend/, con el entorno virtual activado y el `.env`
apuntando a la base real):

    python resetear_password_admin.py <usuario> <contraseña_nueva>

Ejemplo:

    python resetear_password_admin.py administrador "UnaClaveNueva123"

Deja al usuario con esa contraseña y `debe_cambiar_password=True`, así
que el panel le va a pedir elegir una propia (que solo él sepa) apenas
entre con esta temporal -- ver `frontend/src/pages/CambiarPassword.jsx`.

Si además se perdió el acceso a la máquina/servidor por completo, no hay
script que valga -- en ese caso hace falta acceso directo a la base de
datos (por ejemplo `psql`) para poner un `password_hash` nuevo a mano, o
restaurar desde un respaldo.
"""
import sys

from app import models, services
from app.database import SessionLocal


def main():
    if len(sys.argv) != 3:
        print(f"Uso: python {sys.argv[0]} <usuario> <contraseña_nueva>")
        sys.exit(1)

    nombre_usuario, password_nueva = sys.argv[1], sys.argv[2]

    if len(password_nueva) < 8:
        print("La contraseña nueva debe tener al menos 8 caracteres.")
        sys.exit(1)

    db = SessionLocal()
    try:
        usuario = (
            db.query(models.Usuario)
            .filter(models.Usuario.usuario == nombre_usuario)
            .first()
        )
        if not usuario:
            print(f"No existe ningún usuario '{nombre_usuario}'.")
            disponibles = [u.usuario for u in db.query(models.Usuario).all()]
            if disponibles:
                print(f"Usuarios que sí existen: {', '.join(disponibles)}")
            sys.exit(1)

        usuario.password_hash = services.hash_password(password_nueva)
        usuario.debe_cambiar_password = True
        usuario.estado = True  # por si además estaba deshabilitado
        db.commit()

        print(f"Listo -- '{nombre_usuario}' ya puede entrar con la contraseña nueva.")
        print("El panel le va a pedir cambiarla por una propia apenas entre.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
