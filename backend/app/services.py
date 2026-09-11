"""
Lógica de negocio: lectura del QR, identificación de la persona,
lógica temporal ENTRADA/SALIDA y autenticación del panel.

Sigue el flujo funcional descrito en la sección 6 del documento:
1. Se extrae idperfil del contenido del QR.
2. Se busca primero en la base local.
3. Si no existe, se consulta AcademicOK (ver `consultar_fuente_institucional`;
   hoy es scraping de la página pública, mañana será la API oficial que
   confirme TI — solo cambia esa función, el resto del flujo no).
4. Si tampoco se encuentra ahí, se deniega el acceso.
5. Se guarda/actualiza la persona localmente.
6. Se determina ENTRADA o SALIDA según el último movimiento.
7. Se registra el movimiento con fecha/hora y punto de acceso.
"""
import os
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import parse_qs, urlparse

import bcrypt
import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app import models, schema

# --------------------------------------------------------------------------
# Configuración de autenticación
# --------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "cambiar-esta-clave-en-produccion")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

# --------------------------------------------------------------------------
# Configuración de AcademicOK
# --------------------------------------------------------------------------
ACADEMICOK_URL = os.getenv("ACADEMICOK_URL", "https://its.academicok.com/datoscredencial")
ACADEMICOK_TIMEOUT = int(os.getenv("ACADEMICOK_TIMEOUT", "10"))


# --------------------------------------------------------------------------
# QR -> idperfil
# --------------------------------------------------------------------------
def extraer_idperfil(qr_contenido: str) -> Optional[str]:
    """
    El QR de la credencial contiene una URL del tipo:
    https://its.academicok.com/datoscredencial?idperfil=IDPERFIL

    Se intenta primero un parseo formal de URL y, si falla, una
    búsqueda del patrón idperfil=... como respaldo.
    """
    try:
        parsed = urlparse(qr_contenido)
        if parsed.query:
            valores = parse_qs(parsed.query)
            if valores.get("idperfil"):
                return valores["idperfil"][0]
    except Exception:
        pass

    match = re.search(r"idperfil=([^&\s]+)", qr_contenido)
    if match:
        return match.group(1)

    return None


# --------------------------------------------------------------------------
# Consulta a la fuente institucional (AcademicOK)
# --------------------------------------------------------------------------
def consultar_fuente_institucional(idperfil: str) -> Optional[dict]:
    """
    Punto único de integración con AcademicOK.

    Es un scraping de la página pública `datoscredencial` (no hay todavía
    una API oficial confirmada por TI — ver secciones 4 y 13 del documento
    técnico); en cuanto TI defina el endpoint real, este es el único lugar
    que hay que reemplazar, el resto del flujo no cambia.

    Extrae nombre, cédula y correo institucional, siguiendo la prueba de
    concepto validada por el usuario (lectura de QR + BeautifulSoup).
    """
    try:
        parametros = {"action": "consulta", "id": idperfil}
        respuesta = requests.get(
            ACADEMICOK_URL, params=parametros, timeout=ACADEMICOK_TIMEOUT
        )

        if respuesta.status_code != 200:
            return None

        soup = BeautifulSoup(respuesta.text, "html.parser")

        # Nombre completo
        elemento_nombre = soup.find("h5")
        nombre = elemento_nombre.get_text(" ", strip=True) if elemento_nombre else None

        # Cédula / número de identificación
        texto = soup.get_text(" ", strip=True)
        coincidencia_cedula = re.search(r"No\.?\s*Identificaci[oó]n:\s*(\d+)", texto)
        cedula = coincidencia_cedula.group(1) if coincidencia_cedula else None

        # Correo institucional
        correo = None
        for elemento in soup.find_all("h6"):
            texto_elemento = elemento.get_text(" ", strip=True)
            if "Correo Institucional:" in texto_elemento:
                coincidencia_correo = re.search(
                    r"Correo Institucional:\s*"
                    r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
                    texto_elemento,
                    re.IGNORECASE,
                )
                if coincidencia_correo:
                    correo = coincidencia_correo.group(1)
                    break

        if not nombre or not cedula:
            return None

        return {
            "idperfil": idperfil,
            "nombre": nombre,
            "cedula": cedula,
            "correo": correo,
        }

    except requests.RequestException:
        return None
    except Exception:
        return None


# --------------------------------------------------------------------------
# Personal
# --------------------------------------------------------------------------
def obtener_o_crear_personal(
    db: Session, idperfil: Optional[str], datos_externos: Optional[dict]
) -> Optional[models.Personal]:
    persona = None

    if idperfil:
        persona = (
            db.query(models.Personal).filter(models.Personal.idperfil == idperfil).first()
        )

    if not persona and datos_externos and datos_externos.get("cedula"):
        persona = (
            db.query(models.Personal)
            .filter(models.Personal.cedula == datos_externos["cedula"])
            .first()
        )

    # AcademicOK devuelve el nombre completo en un solo campo ("nombre"),
    # no separado en nombres/apellidos. Se guarda tal cual en `nombres` y
    # `apellidos` queda vacío — no se intenta adivinar dónde corta el
    # nombre de los apellidos.
    if persona and datos_externos:
        if datos_externos.get("cedula"):
            persona.cedula = datos_externos["cedula"]
        if datos_externos.get("nombre"):
            persona.nombres = datos_externos["nombre"]
        if datos_externos.get("correo"):
            persona.correo = datos_externos["correo"]
        if idperfil:
            persona.idperfil = idperfil
        persona.ultima_actualizacion = models.ahora_ecuador()
        db.commit()
        db.refresh(persona)
        return persona

    if not persona and datos_externos and datos_externos.get("cedula"):
        persona = models.Personal(
            idperfil=idperfil,
            cedula=datos_externos["cedula"],
            nombres=datos_externos.get("nombre", ""),
            apellidos=None,
            correo=datos_externos.get("correo"),
        )
        db.add(persona)
        db.commit()
        db.refresh(persona)

    return persona


def esta_dentro(db: Session, personal_id: int) -> bool:
    """Regla validada: si la última lectura fue ENTRADA, está dentro."""
    ultimo = (
        db.query(models.Movimiento)
        .filter(models.Movimiento.personal_id == personal_id)
        .order_by(models.Movimiento.fecha_hora.desc())
        .first()
    )
    return bool(ultimo and ultimo.tipo == models.TipoMovimiento.ENTRADA)


def registrar_movimiento(db: Session, personal_id: int, punto_acceso_id: int) -> models.Movimiento:
    tipo = (
        models.TipoMovimiento.SALIDA
        if esta_dentro(db, personal_id)
        else models.TipoMovimiento.ENTRADA
    )
    movimiento = models.Movimiento(
        personal_id=personal_id,
        tipo=tipo,
        punto_acceso_id=punto_acceso_id,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento


def procesar_acceso(db: Session, qr: str, punto_acceso_id: int) -> schema.AccesoResponse:
    idperfil = extraer_idperfil(qr)

    persona = None
    if idperfil:
        persona = (
            db.query(models.Personal).filter(models.Personal.idperfil == idperfil).first()
        )

    if not persona:
        datos_externos = consultar_fuente_institucional(idperfil) if idperfil else None
        persona = obtener_o_crear_personal(db, idperfil, datos_externos)

    if not persona:
        return schema.AccesoResponse(
            resultado="DENEGADO",
            mensaje="No se pudo identificar a la persona a partir del QR.",
        )

    if persona.estado != models.EstadoPersonal.ACTIVO:
        return schema.AccesoResponse(
            resultado="DENEGADO",
            mensaje="La persona no está activa en el sistema.",
            persona=persona,
        )

    punto = (
        db.query(models.PuntoAcceso).filter(models.PuntoAcceso.id == punto_acceso_id).first()
    )
    if not punto or not punto.estado:
        raise HTTPException(status_code=400, detail="Punto de acceso inválido o inactivo.")

    movimiento = registrar_movimiento(db, persona.id, punto_acceso_id)

    return schema.AccesoResponse(
        resultado=movimiento.tipo.value,
        mensaje=f"{movimiento.tipo.value} registrada correctamente.",
        persona=persona,
        fecha_hora=movimiento.fecha_hora,
    )


# --------------------------------------------------------------------------
# Autenticación del panel administrativo
#
# Se usa `bcrypt` directamente (no `passlib`): passlib está sin
# mantenimiento y su detección de versión de bcrypt se rompe con
# versiones nuevas de la librería (falla con "password cannot be
# longer than 72 bytes" al hashear, aunque la contraseña sea corta).
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    # bcrypt solo usa los primeros 72 bytes de la contraseña; se trunca
    # explícitamente para evitar que la librería lo rechace.
    password_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    password_bytes = password.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except ValueError:
        # Hash con un formato inválido/corrupto en la base.
        return False


def autenticar_usuario(db: Session, usuario: str, password: str) -> Optional[models.Usuario]:
    user = db.query(models.Usuario).filter(models.Usuario.usuario == usuario).first()
    if not user or not user.estado:
        return None
    if not verificar_password(password, user.password_hash):
        return None
    return user


def crear_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
