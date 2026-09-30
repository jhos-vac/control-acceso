"""
Lógica del apartado de Reportes del panel: cálculo de estadísticas por
rango de fechas (entradas, salidas, incidencias) y generación del PDF
descargable.

Una "incidencia" es una persona que registró una ENTRADA un día ya
terminado, y cuyo último movimiento de ese mismo día siguió siendo esa
ENTRADA — es decir, no se le registró una SALIDA ese día (ver
`calcular_reporte`). Si el rango incluye el día de hoy y alguien entró
pero todavía no salió, eso NO se cuenta como incidencia (puede seguir
dentro del edificio en este momento) — se reporta aparte, en
`actualmente_dentro`.
"""
import io
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app import models
from app.database import CLAVE_BLOQUEO_NOTIFICACIONES, bloquear_transaccion

# --------------------------------------------------------------------------
# Estilo / branding (mismo color institucional que el panel: #009EAD)
# --------------------------------------------------------------------------
COLOR_MARCA = colors.HexColor("#009EAD")
COLOR_MARCA_CLARO = colors.HexColor("#E6F7F8")
COLOR_TEXTO = colors.HexColor("#1F2937")
COLOR_GRIS = colors.HexColor("#64748B")
COLOR_BORDE = colors.HexColor("#E2E8F0")
COLOR_ROJO_CLARO = colors.HexColor("#FEF2F2")
COLOR_ROJO_TEXTO = colors.HexColor("#B91C1C")

ETIQUETAS_TIPO = {
    "diario": "Reporte diario",
    "semanal": "Reporte semanal",
    "mensual": "Reporte mensual",
    "personalizado": "Reporte personalizado",
}

MESES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _fmt_fecha(d: date) -> str:
    return f"{d.day} de {MESES[d.month]} de {d.year}"


def _fmt_fecha_corta(d: date) -> str:
    return f"{DIAS_SEMANA[d.weekday()][:3].capitalize()} {d.day:02d}/{d.month:02d}"


def _fmt_hora(dt: datetime) -> str:
    return dt.strftime("%H:%M")


# --------------------------------------------------------------------------
# Cálculo del reporte
# --------------------------------------------------------------------------
def calcular_reporte(
    db: Session, desde: date, hasta: date, punto_acceso_id: Optional[int] = None
) -> dict:
    if hasta < desde:
        desde, hasta = hasta, desde

    inicio_dt = datetime.combine(desde, time.min)
    fin_dt = datetime.combine(hasta, time.max)

    query = db.query(models.Movimiento).filter(
        models.Movimiento.fecha_hora >= inicio_dt,
        models.Movimiento.fecha_hora <= fin_dt,
    )
    if punto_acceso_id:
        query = query.filter(models.Movimiento.punto_acceso_id == punto_acceso_id)

    movimientos = query.order_by(models.Movimiento.fecha_hora.asc()).all()

    total_entradas = sum(1 for m in movimientos if m.tipo == models.TipoMovimiento.ENTRADA)
    total_salidas = sum(1 for m in movimientos if m.tipo == models.TipoMovimiento.SALIDA)
    personas_entraron = {m.personal_id for m in movimientos if m.tipo == models.TipoMovimiento.ENTRADA}
    personas_salieron = {m.personal_id for m in movimientos if m.tipo == models.TipoMovimiento.SALIDA}

    # Desglose por día (incluye días sin movimientos, para que se note el hueco)
    por_dia = {}
    cursor = desde
    while cursor <= hasta:
        por_dia[cursor] = {"fecha": cursor, "entradas": 0, "salidas": 0}
        cursor += timedelta(days=1)

    grupos = defaultdict(list)  # (personal_id, dia) -> [movimientos]
    for m in movimientos:
        dia = m.fecha_hora.date()
        if m.tipo == models.TipoMovimiento.ENTRADA:
            por_dia[dia]["entradas"] += 1
        else:
            por_dia[dia]["salidas"] += 1
        grupos[(m.personal_id, dia)].append(m)

    hoy = models.ahora_ecuador().date()
    incidencias = []       # entrada sin salida en un día ya terminado
    actualmente_dentro = []  # entrada de hoy sin salida todavía (no es un error)

    for (_personal_id, dia), movs in grupos.items():
        ultimo = max(movs, key=lambda m: m.fecha_hora)
        if ultimo.tipo != models.TipoMovimiento.ENTRADA:
            continue
        if dia < hoy:
            incidencias.append(ultimo)
        elif dia == hoy:
            actualmente_dentro.append(ultimo)

    incidencias.sort(key=lambda m: m.fecha_hora)
    actualmente_dentro.sort(key=lambda m: m.fecha_hora)

    return {
        "desde": desde,
        "hasta": hasta,
        "total_entradas": total_entradas,
        "total_salidas": total_salidas,
        "personas_entraron": len(personas_entraron),
        "personas_salieron": len(personas_salieron),
        "por_dia": sorted(por_dia.values(), key=lambda d: d["fecha"]),
        "incidencias": incidencias,
        "actualmente_dentro": actualmente_dentro,
    }


# --------------------------------------------------------------------------
# Generación del PDF
# --------------------------------------------------------------------------
def _pie_de_pagina(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(COLOR_BORDE)
    canvas.line(20 * mm, 15 * mm, A4[0] - 20 * mm, 15 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(COLOR_GRIS)
    canvas.drawString(20 * mm, 10 * mm, "Sistema de Control de Acceso — generado automáticamente")
    canvas.drawRightString(A4[0] - 20 * mm, 10 * mm, f"Página {canvas.getPageNumber()}")
    canvas.restoreState()


def _nombre_persona(persona) -> str:
    if not persona:
        return "(persona no identificada)"
    partes = [p for p in [persona.nombres, persona.apellidos] if p]
    return " ".join(partes) if partes else "(sin nombre)"


def generar_pdf(
    reporte: dict,
    tipo: str = "personalizado",
    punto_nombre: Optional[str] = None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title=ETIQUETAS_TIPO.get(tipo, "Reporte"),
    )

    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloReporte", parent=estilos["Heading1"], textColor=COLOR_MARCA,
        fontSize=18, spaceAfter=2,
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloReporte", parent=estilos["Normal"], textColor=COLOR_GRIS,
        fontSize=10, spaceAfter=0,
    )
    estilo_seccion = ParagraphStyle(
        "Seccion", parent=estilos["Heading2"], textColor=COLOR_TEXTO,
        fontSize=12, spaceBefore=14, spaceAfter=6,
    )
    estilo_nota = ParagraphStyle(
        "Nota", parent=estilos["Normal"], textColor=COLOR_GRIS, fontSize=9,
        alignment=TA_LEFT, spaceBefore=4,
    )
    estilo_celda = ParagraphStyle(
        "Celda", parent=estilos["Normal"], textColor=COLOR_TEXTO, fontSize=8.5,
        alignment=TA_LEFT, leading=10,
    )

    def encabezado(texto):
        # Paragraph en vez de string plano: si el texto no entra en el
        # ancho de la columna, se ajusta en 2 líneas en vez de desbordar
        # fuera de la celda. "\n" se convierte en salto de línea manual.
        return Paragraph(texto.replace("\n", "<br/>"), ParagraphStyle(
            "Encabezado", fontName="Helvetica-Bold", fontSize=8.5,
            textColor=colors.white, leading=10,
        ))

    def celda(texto):
        return Paragraph(str(texto), estilo_celda)

    desde, hasta = reporte["desde"], reporte["hasta"]
    if desde == hasta:
        periodo = _fmt_fecha(desde)
    else:
        periodo = f"{_fmt_fecha(desde)} — {_fmt_fecha(hasta)}"

    story = []
    story.append(Paragraph(ETIQUETAS_TIPO.get(tipo, "Reporte"), estilo_titulo))
    story.append(Paragraph(periodo, estilo_subtitulo))
    story.append(Paragraph(
        f"Punto de acceso: {punto_nombre or 'Todos los puntos de acceso'} · "
        f"Generado el {_fmt_fecha(models.ahora_ecuador().date())} a las "
        f"{_fmt_hora(models.ahora_ecuador())}",
        estilo_subtitulo,
    ))
    story.append(Spacer(1, 12))

    # ---- Tarjetas de resumen -------------------------------------------------
    def tarjeta(valor, etiqueta, color_fondo=COLOR_MARCA_CLARO, color_texto=COLOR_MARCA):
        return Table(
            [[Paragraph(str(valor), ParagraphStyle(
                "valor", fontSize=20, textColor=color_texto, fontName="Helvetica-Bold",
                alignment=TA_LEFT,
            ))],
             [Paragraph(etiqueta, ParagraphStyle(
                 "etiqueta", fontSize=8.5, textColor=COLOR_GRIS, alignment=TA_LEFT,
             ))]],
            colWidths=[33 * mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), color_fondo),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
            ]),
        )

    tarjetas = [
        tarjeta(reporte["total_entradas"], "Entradas registradas"),
        tarjeta(reporte["total_salidas"], "Salidas registradas"),
        tarjeta(reporte["personas_entraron"], "Personas distintas\nque ingresaron"),
        tarjeta(
            len(reporte["incidencias"]), "Incidencias\n(sin salida registrada)",
            color_fondo=(COLOR_ROJO_CLARO if reporte["incidencias"] else COLOR_MARCA_CLARO),
            color_texto=(COLOR_ROJO_TEXTO if reporte["incidencias"] else COLOR_MARCA),
        ),
    ]
    fila_tarjetas = Table(
        [tarjetas], colWidths=[36 * mm] * 4,
        style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]),
    )
    story.append(fila_tarjetas)

    # ---- Desglose por día -----------------------------------------------------
    story.append(Paragraph("Entradas y salidas por día", estilo_seccion))
    filas = [[encabezado("Fecha"), encabezado("Entradas"), encabezado("Salidas")]]
    for d in reporte["por_dia"]:
        filas.append([_fmt_fecha_corta(d["fecha"]), str(d["entradas"]), str(d["salidas"])])
    tabla_dias = Table(filas, colWidths=[70 * mm, 40 * mm, 40 * mm], repeatRows=1)
    tabla_dias.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_MARCA),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_MARCA_CLARO]),
        ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(tabla_dias)

    # ---- Incidencias ------------------------------------------------------
    story.append(Paragraph("Incidencias — entrada sin salida registrada ese día", estilo_seccion))
    if not reporte["incidencias"]:
        story.append(Paragraph("No se encontraron incidencias en este período.", estilo_nota))
    else:
        filas_inc = [[
            encabezado("Fecha"), encabezado("Persona"), encabezado("Cédula"),
            encabezado("Hora de\nentrada"), encabezado("Punto de\nacceso"),
        ]]
        for mov in reporte["incidencias"]:
            filas_inc.append([
                _fmt_fecha_corta(mov.fecha_hora.date()),
                celda(_nombre_persona(mov.persona)),
                mov.persona.cedula if mov.persona else "—",
                _fmt_hora(mov.fecha_hora),
                celda(mov.punto_acceso.nombre if mov.punto_acceso else f"#{mov.punto_acceso_id}"),
            ])
        tabla_inc = Table(
            filas_inc, colWidths=[20 * mm, 46 * mm, 26 * mm, 24 * mm, 34 * mm], repeatRows=1,
        )
        tabla_inc.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ROJO_TEXTO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_ROJO_CLARO]),
            ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tabla_inc)

    # ---- Actualmente dentro (solo si el período incluye hoy) --------------
    if reporte["actualmente_dentro"]:
        story.append(Paragraph(
            "Personas dentro del edificio al momento de este reporte", estilo_seccion,
        ))
        story.append(Paragraph(
            "Entraron hoy y todavía no registran salida — no se cuenta como "
            "incidencia mientras el día no haya terminado.", estilo_nota,
        ))
        filas_dentro = [[
            encabezado("Persona"), encabezado("Cédula"),
            encabezado("Hora de\nentrada"), encabezado("Punto de\nacceso"),
        ]]
        for mov in reporte["actualmente_dentro"]:
            filas_dentro.append([
                celda(_nombre_persona(mov.persona)),
                mov.persona.cedula if mov.persona else "—",
                _fmt_hora(mov.fecha_hora),
                celda(mov.punto_acceso.nombre if mov.punto_acceso else f"#{mov.punto_acceso_id}"),
            ])
        tabla_dentro = Table(filas_dentro, colWidths=[50 * mm, 30 * mm, 26 * mm, 34 * mm], repeatRows=1)
        tabla_dentro.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_GRIS),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(Spacer(1, 4))
        story.append(tabla_dentro)

    doc.build(story, onFirstPage=_pie_de_pagina, onLaterPages=_pie_de_pagina)
    return buffer.getvalue()


# --------------------------------------------------------------------------
# Notificación diaria ("el reporte de ayer ya está listo")
# --------------------------------------------------------------------------
def generar_notificacion_reporte_diario(db: Session, dia: date) -> Optional[models.Notificacion]:
    """
    Calcula el reporte de un solo día (`dia`, normalmente "ayer") y crea
    la notificación para la campana del panel, si no existe ya una para
    ese mismo día (evita duplicados si el backend se reinicia el mismo
    día, o si se llama más de una vez a propósito).
    """
    # Con varios workers de Uvicorn (producción), todos ejecutan esta tarea
    # a la vez al arrancar: sin este bloqueo, dos podrían pasar el "ya
    # existe?" de abajo antes de que el otro guarde y crear la notificación
    # por duplicado. El bloqueo se libera solo con el commit/cierre.
    bloquear_transaccion(db, CLAVE_BLOQUEO_NOTIFICACIONES)

    ya_existe = (
        db.query(models.Notificacion)
        .filter(
            models.Notificacion.tipo == "reporte_diario",
            models.Notificacion.desde == dia,
            models.Notificacion.hasta == dia,
        )
        .first()
    )
    if ya_existe:
        return None

    datos = calcular_reporte(db, dia, dia)
    n_incidencias = len(datos["incidencias"])
    resumen_incidencias = (
        f"{n_incidencias} incidencia{'s' if n_incidencias != 1 else ''}"
        if n_incidencias
        else "sin incidencias"
    )
    mensaje = (
        f"{datos['total_entradas']} entradas, {datos['total_salidas']} salidas, "
        f"{resumen_incidencias}."
    )

    notificacion = models.Notificacion(
        tipo="reporte_diario",
        titulo=f"Reporte del {_fmt_fecha(dia)} listo",
        mensaje=mensaje,
        desde=dia,
        hasta=dia,
    )
    db.add(notificacion)
    db.commit()
    db.refresh(notificacion)
    return notificacion
