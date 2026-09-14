"""
Tarea en segundo plano que genera, una vez al día, la notificación
"el reporte de ayer ya está listo" para la campana del panel.

No se usa una librería externa (APScheduler, Celery, etc.) a propósito:
alcanza con una tarea asyncio simple que calcula cuánto falta para la
próxima hora objetivo y se duerme hasta entonces — un backend de este
tamaño no necesita más. Se puede cambiar la hora con la variable de
entorno HORA_NOTIFICACION_DIARIA (formato "HH:MM", hora de Ecuador).
"""
import asyncio
import os
from datetime import datetime, timedelta

from app import models, reportes
from app.database import SessionLocal

HORA_NOTIFICACION_DIARIA = os.getenv("HORA_NOTIFICACION_DIARIA", "06:00")


def _proxima_hora_objetivo(ahora: datetime) -> datetime:
    try:
        hora, minuto = (int(p) for p in HORA_NOTIFICACION_DIARIA.split(":"))
    except ValueError:
        hora, minuto = 6, 0
    objetivo = ahora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    if objetivo <= ahora:
        objetivo += timedelta(days=1)
    return objetivo


def _generar_para_ayer():
    db = SessionLocal()
    try:
        ayer = models.ahora_ecuador().date() - timedelta(days=1)
        notificacion = reportes.generar_notificacion_reporte_diario(db, ayer)
        if notificacion:
            print(f"[notificaciones] Reporte diario del {ayer} generado.")
    except Exception as error:  # nunca debe tumbar el backend por esto
        print(f"[notificaciones] No se pudo generar el reporte diario: {error}")
    finally:
        db.close()


async def _bucle_programador():
    # "Catch-up": si el backend estuvo apagado a la hora objetivo (p.ej.
    # se reinició tarde, o recién se instaló esta función), igual genera
    # la notificación de ayer apenas arranca, en vez de esperar a la
    # próxima hora objetivo.
    await asyncio.get_event_loop().run_in_executor(None, _generar_para_ayer)

    while True:
        ahora = models.ahora_ecuador()
        objetivo = _proxima_hora_objetivo(ahora)
        segundos_espera = (objetivo - ahora).total_seconds()
        await asyncio.sleep(max(segundos_espera, 1))
        await asyncio.get_event_loop().run_in_executor(None, _generar_para_ayer)


def iniciar_programador_notificaciones() -> asyncio.Task:
    return asyncio.create_task(_bucle_programador())
