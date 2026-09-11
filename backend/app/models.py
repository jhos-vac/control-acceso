"""
Modelos ORM (SQLAlchemy) que reflejan las tablas propuestas en el
documento técnico, sección 7 "Base de datos inicial":

- personal        -> cache/referencia local del personal
- movimientos     -> historial de ENTRADA / SALIDA
- puntos_acceso   -> terminales / puntos de acceso
- usuarios        -> usuarios del panel administrativo
"""
import enum
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base

ZONA_ECUADOR = ZoneInfo("America/Guayaquil")


def ahora_ecuador() -> datetime:
    """
    Hora actual "de pared" en Ecuador (sin info de zona horaria), para
    guardar en columnas DateTime naive. Todo el sistema es de un solo
    edificio en Ecuador, así que se evita a propósito guardar en UTC:
    así no hay conversión de por medio que el frontend pueda interpretar
    mal (ver bug reportado: se mostraban movimientos con 5 horas de más,
    justo el offset de UTC-5).
    """
    return datetime.now(ZONA_ECUADOR).replace(tzinfo=None)


class TipoMovimiento(str, enum.Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"


class EstadoPersonal(str, enum.Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"


class RolUsuario(str, enum.Enum):
    ADMIN = "ADMIN"
    OPERADOR = "OPERADOR"


class Personal(Base):
    """Referencia/cache local del personal (docentes, empleados, etc.)."""

    __tablename__ = "personal"

    id = Column(Integer, primary_key=True, index=True)

    # Identificador que viene directamente en el QR de la credencial.
    # Puede ser nulo mientras no se confirme la API institucional.
    idperfil = Column(String(50), unique=True, index=True, nullable=True)

    # Vínculo alterno recomendado por el documento mientras se define
    # la API: no se relacionan personas por nombre.
    cedula = Column(String(20), unique=True, index=True, nullable=False)

    # AcademicOK devuelve el nombre completo en un solo campo; se guarda
    # en "nombres" y "apellidos" queda opcional (no se intenta separar).
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=True)
    correo = Column(String(150), nullable=True)

    estado = Column(Enum(EstadoPersonal), default=EstadoPersonal.ACTIVO, nullable=False)

    fecha_registro = Column(DateTime, default=ahora_ecuador, nullable=False)
    ultima_actualizacion = Column(
        DateTime, default=ahora_ecuador, onupdate=ahora_ecuador, nullable=False
    )

    movimientos = relationship(
        "Movimiento", back_populates="persona", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - solo utilidad de debug
        return f"<Personal id={self.id} cedula={self.cedula} {self.nombres} {self.apellidos}>"


class PuntoAcceso(Base):
    """Terminal físico (ej. Raspberry Pi con lector QR) o puerta controlada."""

    __tablename__ = "puntos_acceso"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    ubicacion = Column(String(150), nullable=True)
    estado = Column(Boolean, default=True, nullable=False)  # activo/inactivo

    movimientos = relationship("Movimiento", back_populates="punto_acceso")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PuntoAcceso id={self.id} nombre={self.nombre}>"


class Movimiento(Base):
    """Historial de ENTRADA / SALIDA registrado por cada persona."""

    __tablename__ = "movimientos"

    id = Column(Integer, primary_key=True, index=True)
    personal_id = Column(Integer, ForeignKey("personal.id"), nullable=False, index=True)
    tipo = Column(Enum(TipoMovimiento), nullable=False)
    fecha_hora = Column(DateTime, default=ahora_ecuador, nullable=False, index=True)
    punto_acceso_id = Column(Integer, ForeignKey("puntos_acceso.id"), nullable=False)

    persona = relationship("Personal", back_populates="movimientos")
    punto_acceso = relationship("PuntoAcceso", back_populates="movimientos")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Movimiento id={self.id} tipo={self.tipo} personal_id={self.personal_id}>"


class Usuario(Base):
    """Usuario del panel administrativo (no confundir con 'personal')."""

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    usuario = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(RolUsuario), default=RolUsuario.OPERADOR, nullable=False)
    estado = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Usuario id={self.id} usuario={self.usuario} rol={self.rol}>"
