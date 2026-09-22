"""
Esquemas Pydantic usados para validar entradas y dar forma a las
respuestas de la API (independientes de los modelos ORM).
"""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models import EstadoPersonal, RolUsuario, TipoMovimiento


# --------------------------------------------------------------------------
# Personal
# --------------------------------------------------------------------------
class PersonalBase(BaseModel):
    cedula: str
    nombres: str
    apellidos: Optional[str] = None
    correo: Optional[str] = None
    idperfil: Optional[str] = None
    estado: EstadoPersonal = EstadoPersonal.ACTIVO


class PersonalCreate(PersonalBase):
    pass


class PersonalOut(PersonalBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_registro: datetime
    ultima_actualizacion: datetime


# --------------------------------------------------------------------------
# Puntos de acceso
# --------------------------------------------------------------------------
class PuntoAccesoBase(BaseModel):
    nombre: str
    ubicacion: Optional[str] = None
    estado: bool = True
    mac_address: Optional[str] = None  # para poder encenderlo a distancia (Wake-on-LAN)


class PuntoAccesoCreate(PuntoAccesoBase):
    pass


class PuntoAccesoUpdate(BaseModel):
    """Todos los campos opcionales: se actualiza solo lo que se envíe
    (p.ej. agregar la MAC de un punto de acceso que ya existía)."""

    nombre: Optional[str] = None
    ubicacion: Optional[str] = None
    estado: Optional[bool] = None
    mac_address: Optional[str] = None


class PuntoAccesoOut(PuntoAccesoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    en_linea: bool = False
    ultimo_latido: Optional[datetime] = None


class LatidoResponse(BaseModel):
    comando: Optional[str] = None


class ComandoRequest(BaseModel):
    comando: str  # hoy solo "APAGAR"


# --------------------------------------------------------------------------
# Movimientos
# --------------------------------------------------------------------------
class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    personal_id: int
    tipo: TipoMovimiento
    fecha_hora: datetime
    punto_acceso_id: int
    persona: Optional[PersonalOut] = None


# --------------------------------------------------------------------------
# Reportes
# --------------------------------------------------------------------------
class ReporteDiaOut(BaseModel):
    fecha: date
    entradas: int
    salidas: int


class ReporteResumenOut(BaseModel):
    desde: date
    hasta: date
    total_entradas: int
    total_salidas: int
    personas_entraron: int
    personas_salieron: int
    por_dia: List[ReporteDiaOut]
    incidencias: List[MovimientoOut]
    actualmente_dentro: List[MovimientoOut]


# --------------------------------------------------------------------------
# Notificaciones
# --------------------------------------------------------------------------
class NotificacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    titulo: str
    mensaje: str
    desde: Optional[date] = None
    hasta: Optional[date] = None
    leida: bool
    fecha_creacion: datetime


# --------------------------------------------------------------------------
# Acceso (endpoint principal usado por el terminal QR)
# --------------------------------------------------------------------------
class AccesoRequest(BaseModel):
    qr: str
    punto_acceso: int
    # Momento REAL en que el terminal leyó el QR -- no cuándo lo manda al
    # backend. Importante para la cola local sin conexión: un terminal
    # puede leer varios códigos mientras no hay red y enviarlos recién
    # cuando vuelve, minutos u horas después; sin este campo todos
    # quedarían con la hora de envío, no la de la lectura real. Opcional:
    # si no se manda, el backend usa su propia hora.
    fecha_hora_cliente: Optional[datetime] = None


class AccesoResponse(BaseModel):
    resultado: str  # "ENTRADA" | "SALIDA" | "DENEGADO" | "DUPLICADO"
    mensaje: str
    persona: Optional[PersonalOut] = None
    fecha_hora: Optional[datetime] = None
    # Solo viene en "DUPLICADO": qué tipo de movimiento fue el que ya
    # estaba registrado (para que el terminal pueda mostrar, por ejemplo,
    # "Ya se registró ENTRADA hace 2 min").
    ultimo_tipo: Optional[str] = None


# --------------------------------------------------------------------------
# Usuarios / autenticación del panel
# --------------------------------------------------------------------------
class UsuarioBase(BaseModel):
    nombre: str
    usuario: str
    rol: RolUsuario = RolUsuario.OPERADOR


class UsuarioCreate(UsuarioBase):
    password: str


class UsuarioOut(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado: bool
    debe_cambiar_password: bool


class LoginRequest(BaseModel):
    usuario: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str


class ResetearPasswordRequest(BaseModel):
    # Usado por un ADMIN para resetear la contraseña de OTRO usuario (ver
    # POST /api/usuarios/{id}/resetear-password) -- deja al usuario con
    # esta contraseña temporal y debe_cambiar_password=True, para que la
    # cambie él mismo apenas entre.
    password_temporal: str
