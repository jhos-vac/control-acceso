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
import socket
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
# Estado en línea de los puntos de acceso (latido / heartbeat)
# --------------------------------------------------------------------------
# El terminal manda un latido cada ~15s (ver terminal/leer_qr.py). Si no se
# recibe ninguno en más de este tiempo, se muestra como "sin conexión" en
# el panel (dispositivo apagado, sin red, o el script no está corriendo).
EN_LINEA_SEGUNDOS = int(os.getenv("EN_LINEA_SEGUNDOS", "45"))

# --------------------------------------------------------------------------
# Marca duplicada (ENTRADA/SALIDA repetida por error)
# --------------------------------------------------------------------------
# Si una persona ya tiene un movimiento registrado hace menos de este
# tiempo, un nuevo escaneo NO alterna a ENTRADA/SALIDA -- se responde
# "DUPLICADO" sin crear un movimiento nuevo. Pensado para el caso típico:
# alguien no está seguro si ya marcó, vuelve a escanear "por si acaso", y
# sin esto quedaría con una SALIDA falsa (o una ENTRADA falsa) unos
# segundos después de la marca real.
MINUTOS_ANTIDUPLICADO_MOVIMIENTO = float(os.getenv("MINUTOS_ANTIDUPLICADO_MOVIMIENTO", "5"))

COMANDOS_VALIDOS = {"APAGAR"}

# --------------------------------------------------------------------------
# Encendido remoto (Wake-on-LAN)
# --------------------------------------------------------------------------
# A diferencia de "APAGAR" (que el terminal recoge solo en su próximo
# latido, porque sigue encendido y puede preguntar), encender un equipo que
# ya está apagado no se puede pedir por HTTP normal: no hay nadie del otro
# lado escuchando. La única forma sin hardware extra (un enchufe/relé
# inteligente) es Wake-on-LAN: un "paquete mágico" UDP que se manda por
# broadcast en la red local, dirigido a la MAC del equipo, y que la placa de
# red del equipo detecta incluso estando apagado (si tiene esa función
# habilitada). Limitaciones importantes, que el panel debe dejar claras:
#   - El equipo necesita una MAC configurada en este sistema.
#   - Wake-on-LAN normalmente requiere estar en la MISMA red local que el
#     terminal (broadcast) — no cruza routers salvo que se configure un
#     broadcast dirigido, por eso se puede sobreescribir con
#     WOL_BROADCAST_IP si el backend y el terminal están en una red
#     distinta a 255.255.255.255.
#   - El equipo necesita tener Wake-on-LAN habilitado en el BIOS/UEFI y,
#     casi siempre, estar conectado por cable (no WiFi).
#   - Una Raspberry Pi (el hardware final planeado para el terminal) por lo
#     general NO soporta encenderse así estando completamente apagada —
#     a diferencia de una PC, no mantiene la placa de red con energía en
#     standby. Con una Pi, la alternativa realista es un enchufe/relé
#     inteligente que corte y reponga la energía física.
WOL_BROADCAST_IP = os.getenv("WOL_BROADCAST_IP", "255.255.255.255")
WOL_PUERTO = int(os.getenv("WOL_PUERTO", "9"))

PATRON_MAC = re.compile(r"^[0-9A-Fa-f]{12}$")


def normalizar_mac(mac: str) -> str:
    """Acepta 'AA:BB:CC:DD:EE:FF', 'AA-BB-CC-DD-EE-FF' o 'AABBCCDDEEFF' y
    devuelve siempre 'AA:BB:CC:DD:EE:FF' en mayúsculas. Lanza HTTPException
    si el formato no es una MAC válida de 6 bytes."""
    limpio = re.sub(r"[^0-9A-Fa-f]", "", mac or "")
    if not PATRON_MAC.match(limpio):
        raise HTTPException(
            status_code=400,
            detail="Dirección MAC inválida. Debe tener 6 bytes, ej. AA:BB:CC:DD:EE:FF.",
        )
    return ":".join(limpio[i : i + 2] for i in range(0, 12, 2)).upper()


def construir_paquete_magico(mac: str) -> bytes:
    """6 bytes 0xFF seguidos de la MAC repetida 16 veces — formato estándar
    del 'magic packet' de Wake-on-LAN."""
    mac_bytes = bytes.fromhex(mac.replace(":", ""))
    return b"\xff" * 6 + mac_bytes * 16


def enviar_wol(mac: str, broadcast_ip: str = WOL_BROADCAST_IP, puerto: int = WOL_PUERTO) -> None:
    paquete = construir_paquete_magico(mac)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(paquete, (broadcast_ip, puerto))


def encender_punto_acceso(db: Session, punto_id: int) -> models.PuntoAcceso:
    """Manda el paquete mágico de Wake-on-LAN al punto de acceso indicado.
    No hay forma de confirmar desde acá si el equipo realmente se encendió
    (no hay nadie escuchando todavía) — el panel debe avisar que puede
    tardar y que depende de que el hardware lo soporte."""
    punto = db.query(models.PuntoAcceso).filter(models.PuntoAcceso.id == punto_id).first()
    if not punto:
        raise HTTPException(status_code=404, detail="Punto de acceso no encontrado.")
    if not punto.mac_address:
        raise HTTPException(
            status_code=400,
            detail=(
                "Este punto de acceso no tiene una dirección MAC configurada. "
                "Edítalo para agregarla antes de poder encenderlo a distancia."
            ),
        )
    enviar_wol(punto.mac_address)
    punto.en_linea = esta_en_linea(punto)
    return punto


def actualizar_punto_acceso(
    db: Session, punto_id: int, datos: schema.PuntoAccesoUpdate
) -> models.PuntoAcceso:
    punto = db.query(models.PuntoAcceso).filter(models.PuntoAcceso.id == punto_id).first()
    if not punto:
        raise HTTPException(status_code=404, detail="Punto de acceso no encontrado.")

    cambios = datos.model_dump(exclude_unset=True)
    if "mac_address" in cambios and cambios["mac_address"]:
        cambios["mac_address"] = normalizar_mac(cambios["mac_address"])
    for campo, valor in cambios.items():
        setattr(punto, campo, valor)

    db.commit()
    db.refresh(punto)
    punto.en_linea = esta_en_linea(punto)
    return punto


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


def ultimo_movimiento(db: Session, personal_id: int) -> Optional[models.Movimiento]:
    return (
        db.query(models.Movimiento)
        .filter(models.Movimiento.personal_id == personal_id)
        .order_by(models.Movimiento.fecha_hora.desc())
        .first()
    )


def esta_dentro(db: Session, personal_id: int) -> bool:
    """Regla validada: si la última lectura fue ENTRADA, está dentro."""
    ultimo = ultimo_movimiento(db, personal_id)
    return bool(ultimo and ultimo.tipo == models.TipoMovimiento.ENTRADA)


def _hora_valida_cliente(fecha_hora_cliente: Optional[datetime]) -> datetime:
    """El terminal puede mandar la hora REAL en que se leyó el QR (no la
    hora en que se manda al backend) -- esto importa sobre todo cuando el
    terminal estuvo sin conexión un rato y recién ahora puede enviar lo
    que acumuló: si se usara la hora de envío, todos esos accesos
    quedarían mal ordenados (y la ventana de "marca duplicada" de abajo
    compararía contra el momento equivocado).

    Se usa esa hora tal cual, salvo que sea claramente poco creíble (el
    terminal no tiene batería de respaldo para el reloj -- si pierde
    energía sin red para sincronizar por NTP, puede arrancar con una
    fecha vieja): más de un par de minutos en el futuro (desfase de
    reloj) o más de 30 días en el pasado. En esos casos se usa la hora
    del servidor."""
    ahora = models.ahora_ecuador()
    if fecha_hora_cliente is None:
        return ahora
    diferencia = (ahora - fecha_hora_cliente).total_seconds()
    if diferencia < -120 or diferencia > 30 * 24 * 3600:
        return ahora
    return fecha_hora_cliente


def registrar_movimiento(
    db: Session,
    personal_id: int,
    punto_acceso_id: int,
    fecha_hora: Optional[datetime] = None,
    ultimo: Optional[models.Movimiento] = None,
) -> models.Movimiento:
    if ultimo is None:
        ultimo = ultimo_movimiento(db, personal_id)
    tipo = (
        models.TipoMovimiento.SALIDA
        if (ultimo and ultimo.tipo == models.TipoMovimiento.ENTRADA)
        else models.TipoMovimiento.ENTRADA
    )
    movimiento = models.Movimiento(
        personal_id=personal_id,
        tipo=tipo,
        punto_acceso_id=punto_acceso_id,
        fecha_hora=fecha_hora or models.ahora_ecuador(),
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento


def procesar_acceso(
    db: Session,
    qr: str,
    punto_acceso_id: int,
    fecha_hora_cliente: Optional[datetime] = None,
) -> schema.AccesoResponse:
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

    momento = _hora_valida_cliente(fecha_hora_cliente)
    ultimo = ultimo_movimiento(db, persona.id)

    if ultimo:
        segundos_desde_ultimo = (momento - ultimo.fecha_hora).total_seconds()
        if 0 <= segundos_desde_ultimo < MINUTOS_ANTIDUPLICADO_MOVIMIENTO * 60:
            minutos = int(segundos_desde_ultimo // 60)
            hace = f"{minutos} min" if minutos else f"{int(segundos_desde_ultimo)} s"
            return schema.AccesoResponse(
                resultado="DUPLICADO",
                mensaje=(
                    f"Ya se había registrado {ultimo.tipo.value} hace {hace} -- "
                    "no se volvió a marcar para evitar un duplicado."
                ),
                persona=persona,
                fecha_hora=ultimo.fecha_hora,
                ultimo_tipo=ultimo.tipo.value,
            )

    movimiento = registrar_movimiento(
        db, persona.id, punto_acceso_id, fecha_hora=momento, ultimo=ultimo
    )

    return schema.AccesoResponse(
        resultado=movimiento.tipo.value,
        mensaje=f"{movimiento.tipo.value} registrada correctamente.",
        persona=persona,
        fecha_hora=movimiento.fecha_hora,
    )


def esta_en_linea(punto: models.PuntoAcceso) -> bool:
    if not punto.ultimo_latido:
        return False
    segundos = (models.ahora_ecuador() - punto.ultimo_latido).total_seconds()
    return 0 <= segundos < EN_LINEA_SEGUNDOS


def anotar_en_linea(puntos: list) -> list:
    """Agrega el atributo `en_linea` (no persistido) a cada PuntoAcceso,
    calculado a partir de `ultimo_latido`, para que lo pueda leer el
    schema de salida (PuntoAccesoOut.en_linea)."""
    for punto in puntos:
        punto.en_linea = esta_en_linea(punto)
    return puntos


def registrar_latido(db: Session, punto_id: int) -> tuple[bool, Optional[str]]:
    """Actualiza el latido del punto de acceso y devuelve
    (encontrado, comando_pendiente), limpiando el comando en el mismo
    paso para no reenviarlo dos veces."""
    punto = db.query(models.PuntoAcceso).filter(models.PuntoAcceso.id == punto_id).first()
    if not punto:
        return False, None
    punto.ultimo_latido = models.ahora_ecuador()
    comando = punto.comando_pendiente
    punto.comando_pendiente = None
    db.commit()
    return True, comando


def enviar_comando(db: Session, punto_id: int, comando: str) -> models.PuntoAcceso:
    if comando not in COMANDOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Comando no reconocido.")
    punto = db.query(models.PuntoAcceso).filter(models.PuntoAcceso.id == punto_id).first()
    if not punto:
        raise HTTPException(status_code=404, detail="Punto de acceso no encontrado.")
    punto.comando_pendiente = comando
    db.commit()
    db.refresh(punto)
    punto.en_linea = esta_en_linea(punto)
    return punto


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
