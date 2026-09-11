"""
Esquemas Pydantic usados para validar entradas y dar forma a las
respuestas de la API (independientes de los modelos ORM).
"""
from datetime import datetime
from typing import Optional

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


class PuntoAccesoCreate(PuntoAccesoBase):
    pass


class PuntoAccesoOut(PuntoAccesoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


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
# Acceso (endpoint principal usado por el terminal QR)
# --------------------------------------------------------------------------
class AccesoRequest(BaseModel):
    qr: str
    punto_acceso: int


class AccesoResponse(BaseModel):
    resultado: str  # "ENTRADA" | "SALIDA" | "DENEGADO"
    mensaje: str
    persona: Optional[PersonalOut] = None
    fecha_hora: Optional[datetime] = None


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


class LoginRequest(BaseModel):
    usuario: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
