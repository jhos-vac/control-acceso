"""
Endpoints de la API, según la propuesta de la sección 8 del documento
técnico:

    POST /api/acceso           -> procesar QR y registrar ENTRADA/SALIDA
    GET  /api/personas         -> consultar personal
    GET  /api/personas/dentro  -> consultar personas actualmente dentro
    GET  /api/movimientos      -> consultar historial
    POST /api/login            -> autenticar usuarios del panel

Se agregó además GET /api/puntos-acceso (necesario para poblar el
panel administrativo) y un pequeño mecanismo de autenticación por
JWT para proteger los endpoints de consulta/administración. El
endpoint /api/acceso (usado por el terminal QR) queda sin
autenticación de usuario porque lo usa el propio dispositivo lector,
no una persona con sesión en el panel.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import models, schema, services
from app.database import get_db

router = APIRouter(prefix="/api")

# tokenUrl es solo informativo para la documentación (/docs); el login
# real recibe JSON en el body (ver LoginRequest), no un form OAuth2.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=True)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.Usuario:
    payload = services.decodificar_token(token)
    usuario = payload.get("sub")
    user = db.query(models.Usuario).filter(models.Usuario.usuario == usuario).first()
    if not user or not user.estado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no válido"
        )
    return user


# --------------------------------------------------------------------------
# Acceso (usado por el terminal / lector QR)
# --------------------------------------------------------------------------
@router.post("/acceso", response_model=schema.AccesoResponse, tags=["acceso"])
def registrar_acceso(payload: schema.AccesoRequest, db: Session = Depends(get_db)):
    return services.procesar_acceso(db, payload.qr, payload.punto_acceso)


# --------------------------------------------------------------------------
# Personas
# --------------------------------------------------------------------------
@router.get("/personas", response_model=List[schema.PersonalOut], tags=["personas"])
def listar_personas(
    db: Session = Depends(get_db), _usuario: models.Usuario = Depends(get_current_user)
):
    return db.query(models.Personal).order_by(models.Personal.apellidos).all()


@router.get(
    "/personas/dentro", response_model=List[schema.PersonalOut], tags=["personas"]
)
def personas_dentro(
    db: Session = Depends(get_db), _usuario: models.Usuario = Depends(get_current_user)
):
    """Personas cuyo último movimiento fue ENTRADA (es decir, siguen dentro)."""
    ultimos = (
        db.query(models.Movimiento)
        .order_by(models.Movimiento.personal_id, models.Movimiento.fecha_hora.desc())
        .all()
    )

    vistos = set()
    dentro_ids = []
    for mov in ultimos:
        if mov.personal_id in vistos:
            continue
        vistos.add(mov.personal_id)
        if mov.tipo == models.TipoMovimiento.ENTRADA:
            dentro_ids.append(mov.personal_id)

    if not dentro_ids:
        return []

    return db.query(models.Personal).filter(models.Personal.id.in_(dentro_ids)).all()


# --------------------------------------------------------------------------
# Movimientos
# --------------------------------------------------------------------------
@router.get("/movimientos", response_model=List[schema.MovimientoOut], tags=["movimientos"])
def listar_movimientos(
    personal_id: Optional[int] = None,
    limite: int = 100,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    query = db.query(models.Movimiento)
    if personal_id:
        query = query.filter(models.Movimiento.personal_id == personal_id)
    return query.order_by(models.Movimiento.fecha_hora.desc()).limit(limite).all()


# --------------------------------------------------------------------------
# Puntos de acceso
# --------------------------------------------------------------------------
@router.get(
    "/puntos-acceso", response_model=List[schema.PuntoAccesoOut], tags=["puntos-acceso"]
)
def listar_puntos_acceso(
    db: Session = Depends(get_db), _usuario: models.Usuario = Depends(get_current_user)
):
    return db.query(models.PuntoAcceso).all()


@router.post(
    "/puntos-acceso",
    response_model=schema.PuntoAccesoOut,
    tags=["puntos-acceso"],
    status_code=status.HTTP_201_CREATED,
)
def crear_punto_acceso(
    payload: schema.PuntoAccesoCreate,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    punto = models.PuntoAcceso(**payload.model_dump())
    db.add(punto)
    db.commit()
    db.refresh(punto)
    return punto


# --------------------------------------------------------------------------
# Autenticación del panel
# --------------------------------------------------------------------------
@router.post("/login", response_model=schema.TokenResponse, tags=["auth"])
def login(payload: schema.LoginRequest, db: Session = Depends(get_db)):
    user = services.autenticar_usuario(db, payload.usuario, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )
    token = services.crear_access_token({"sub": user.usuario, "rol": user.rol.value})
    return schema.TokenResponse(access_token=token, usuario=user)
