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
from datetime import date
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import models, reportes, schema, services
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


def get_admin_actual(
    usuario: models.Usuario = Depends(get_current_user),
) -> models.Usuario:
    """Igual que get_current_user, pero además exige rol ADMIN. Se usa
    para acciones sensibles como apagar un punto de acceso a distancia."""
    if usuario.rol != models.RolUsuario.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere un usuario administrador.",
        )
    return usuario


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
    puntos = db.query(models.PuntoAcceso).all()
    return services.anotar_en_linea(puntos)


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
    datos = payload.model_dump()
    if datos.get("mac_address"):
        datos["mac_address"] = services.normalizar_mac(datos["mac_address"])
    punto = models.PuntoAcceso(**datos)
    db.add(punto)
    db.commit()
    db.refresh(punto)
    punto.en_linea = False
    return punto


@router.patch(
    "/puntos-acceso/{punto_id}",
    response_model=schema.PuntoAccesoOut,
    tags=["puntos-acceso"],
)
def editar_punto_acceso(
    punto_id: int,
    payload: schema.PuntoAccesoUpdate,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(get_admin_actual),
):
    """Permite, entre otras cosas, agregarle la dirección MAC a un punto de
    acceso que ya existía (necesaria para poder encenderlo a distancia).
    Requiere ADMIN, igual que crear/apagar/encender."""
    return services.actualizar_punto_acceso(db, punto_id, payload)


@router.post(
    "/puntos-acceso/{punto_id}/latido",
    response_model=schema.LatidoResponse,
    tags=["puntos-acceso"],
)
def latido_punto_acceso(punto_id: int, db: Session = Depends(get_db)):
    """
    Llamado por el terminal (leer_qr.py, y a futuro la Raspberry Pi) cada
    pocos segundos mientras está encendido: avisa que sigue vivo y, en la
    misma respuesta, recoge cualquier comando pendiente (hoy solo
    "APAGAR"). Sin autenticación de usuario, igual que /acceso: lo llama
    el propio dispositivo, no una persona con sesión en el panel.
    """
    encontrado, comando = services.registrar_latido(db, punto_id)
    if not encontrado:
        raise HTTPException(status_code=404, detail="Punto de acceso no encontrado.")
    return schema.LatidoResponse(comando=comando)


@router.post(
    "/puntos-acceso/{punto_id}/comando",
    response_model=schema.PuntoAccesoOut,
    tags=["puntos-acceso"],
)
def enviar_comando_punto_acceso(
    punto_id: int,
    payload: schema.ComandoRequest,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(get_admin_actual),
):
    """Deja un comando pendiente (hoy solo 'APAGAR') para que el terminal
    lo recoja en su próximo latido. Requiere usuario ADMIN: apagar el
    terminal a distancia es una acción sensible (deja el punto de acceso
    sin lector hasta que alguien lo vuelva a encender físicamente)."""
    return services.enviar_comando(db, punto_id, payload.comando.upper())


@router.post(
    "/puntos-acceso/{punto_id}/encender",
    response_model=schema.PuntoAccesoOut,
    tags=["puntos-acceso"],
)
def encender_punto_acceso(
    punto_id: int,
    db: Session = Depends(get_db),
    _admin: models.Usuario = Depends(get_admin_actual),
):
    """Manda un paquete mágico de Wake-on-LAN a la MAC configurada del
    punto de acceso. Requiere ADMIN. No hay confirmación real de que el
    equipo se encendió (no hay nadie escuchando mientras está apagado) —
    solo indica que el paquete se mandó; el panel debe avisar que depende
    de que el hardware/red lo soporten (ver notas en services.py)."""
    return services.encender_punto_acceso(db, punto_id)


# --------------------------------------------------------------------------
# Reportes (diario / semanal / mensual / personalizado)
# --------------------------------------------------------------------------
@router.get(
    "/reportes/resumen", response_model=schema.ReporteResumenOut, tags=["reportes"]
)
def resumen_reporte(
    desde: date = Query(..., description="Fecha inicial (incluida), YYYY-MM-DD"),
    hasta: date = Query(..., description="Fecha final (incluida), YYYY-MM-DD"),
    punto_acceso_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    """Datos del reporte en JSON, para mostrarlo en pantalla antes de (o
    en vez de) descargar el PDF."""
    return reportes.calcular_reporte(db, desde, hasta, punto_acceso_id)


@router.get("/reportes/pdf", tags=["reportes"])
def pdf_reporte(
    desde: date = Query(..., description="Fecha inicial (incluida), YYYY-MM-DD"),
    hasta: date = Query(..., description="Fecha final (incluida), YYYY-MM-DD"),
    punto_acceso_id: Optional[int] = Query(None),
    tipo: str = Query("personalizado", description="diario | semanal | mensual | personalizado"),
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    """Mismo cálculo que /reportes/resumen, pero devuelto como PDF listo
    para descargar."""
    datos = reportes.calcular_reporte(db, desde, hasta, punto_acceso_id)

    punto_nombre = None
    if punto_acceso_id:
        punto = (
            db.query(models.PuntoAcceso).filter(models.PuntoAcceso.id == punto_acceso_id).first()
        )
        punto_nombre = punto.nombre if punto else None

    pdf_bytes = reportes.generar_pdf(datos, tipo=tipo, punto_nombre=punto_nombre)
    nombre_archivo = f"reporte_{tipo}_{desde.isoformat()}_{hasta.isoformat()}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


# --------------------------------------------------------------------------
# Notificaciones (campana del panel)
# --------------------------------------------------------------------------
@router.get(
    "/notificaciones", response_model=List[schema.NotificacionOut], tags=["notificaciones"]
)
def listar_notificaciones(
    solo_no_leidas: bool = False,
    limite: int = 20,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    query = db.query(models.Notificacion)
    if solo_no_leidas:
        query = query.filter(models.Notificacion.leida.is_(False))
    return (
        query.order_by(models.Notificacion.fecha_creacion.desc()).limit(limite).all()
    )


@router.post(
    "/notificaciones/{notificacion_id}/leer",
    response_model=schema.NotificacionOut,
    tags=["notificaciones"],
)
def marcar_notificacion_leida(
    notificacion_id: int,
    db: Session = Depends(get_db),
    _usuario: models.Usuario = Depends(get_current_user),
):
    notificacion = (
        db.query(models.Notificacion)
        .filter(models.Notificacion.id == notificacion_id)
        .first()
    )
    if not notificacion:
        raise HTTPException(status_code=404, detail="Notificación no encontrada.")
    notificacion.leida = True
    db.commit()
    db.refresh(notificacion)
    return notificacion


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
