"""
Validación de la configuración al arrancar.

Con APP_ENV=production (ver .env.production.example) el backend se niega a
arrancar si quedó alguna configuración de desarrollo o un valor de ejemplo
sin reemplazar. Sin esa variable (desarrollo local) no exige nada, para no
complicar las pruebas en la PC.
"""
import os

# Valores de ejemplo/por defecto que jamás deben llegar a producción.
SECRET_KEY_PLACEHOLDERS = (
    "cambiar-esta-clave-en-produccion",
    "cambia-esta-clave-por-una-generada-aleatoriamente",
    "cambiar_por_una_clave_generada_aleatoriamente",
)


def es_produccion() -> bool:
    return os.getenv("APP_ENV", "").strip().lower() == "production"


def problemas_de_configuracion() -> list:
    """Lista de problemas (texto legible) de la configuración actual para
    un entorno de producción. Vacía si todo está bien."""
    problemas = []

    secret_key = os.getenv("SECRET_KEY", "")
    if not secret_key or secret_key.strip().lower() in SECRET_KEY_PLACEHOLDERS:
        problemas.append(
            "SECRET_KEY no está definida o sigue con el valor de ejemplo. "
            'Genera una con: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    elif len(secret_key) < 32:
        problemas.append("SECRET_KEY es demasiado corta (usa al menos 32 caracteres).")

    origenes = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
    if not origenes or "*" in origenes:
        problemas.append(
            "ALLOWED_ORIGINS está vacío o en '*'. Pon la URL del panel, por ejemplo "
            "https://control-acceso.sudamericano.edu.ec"
        )

    if "CAMBIAR" in os.getenv("DATABASE_URL", ""):
        problemas.append("DATABASE_URL todavía tiene el usuario/contraseña de ejemplo (CAMBIAR_...).")

    return problemas


def validar_configuracion() -> None:
    if not es_produccion():
        return

    problemas = problemas_de_configuracion()
    if problemas:
        detalle = "\n".join(f"  - {p}" for p in problemas)
        raise RuntimeError(
            "Configuración de producción inválida (APP_ENV=production):\n" + detalle
        )

    if not os.getenv("TERMINAL_API_KEY", "").strip():
        print(
            "[config] AVISO: TERMINAL_API_KEY no está definida -- /api/acceso y "
            "/api/puntos-acceso/{id}/latido quedan abiertos a cualquiera que conozca la URL."
        )
