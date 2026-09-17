"""
Cola local persistente (SQLite) para los códigos QR leídos, pensada para
dos problemas que pidió resolver el usuario:

1. Velocidad: con afluencia de gente en la entrada, cada persona no puede
   esperar a que el terminal termine de hablar con el backend por red
   antes de poder leer el siguiente código. Por eso, apenas se lee un QR
   se guarda ACÁ (en disco, en milisegundos) y el terminal sigue leyendo
   de inmediato -- el envío real al backend lo hace, en otro hilo y sin
   bloquear nada, `comun.hilo_envio()`.

2. Sin conexión: si no hay red o el backend está caído, los códigos
   leídos NO se pierden -- quedan pendientes acá (en un archivo, no en
   memoria, así que sobreviven un corte de luz o un reinicio del
   terminal) hasta que `comun.hilo_envio()` los pueda mandar. Se procesan
   siempre en el mismo orden en que se leyeron (más viejo primero),
   porque el backend usa ese orden cronológico real para decidir
   ENTRADA/SALIDA de cada persona (ver `fecha_hora_cliente` en
   `backend/README.md`).

No requiere ninguna librería externa -- `sqlite3` viene con Python.
"""
import os
import sqlite3
import threading
from datetime import datetime

_RUTA_DB = os.getenv(
    "COLA_LOCAL_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "cola_local.db"),
)

# Una sola conexión compartida entre los hilos (el hilo que lee QR y el
# que los envía), protegida por un lock propio -- sqlite3 no es seguro
# para usar la misma conexión desde varios hilos sin coordinarse.
_lock = threading.Lock()


def _conectar():
    conexion = sqlite3.connect(_RUTA_DB, check_same_thread=False)
    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS pendientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            origen TEXT NOT NULL,
            fecha_hora TEXT NOT NULL,
            intentos INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conexion.commit()
    return conexion


_conexion = _conectar()


def agregar(codigo, origen, fecha_hora=None):
    """Guarda un código leído en la cola. `fecha_hora` es el momento REAL
    en que se leyó (no cuándo se manda) -- si no se pasa, se usa el
    momento actual. Devuelve el id de la fila creada."""
    momento = fecha_hora or datetime.now()
    with _lock:
        cursor = _conexion.execute(
            "INSERT INTO pendientes (codigo, origen, fecha_hora, intentos) VALUES (?, ?, ?, 0)",
            (codigo, origen, momento.isoformat()),
        )
        _conexion.commit()
        return cursor.lastrowid


def obtener_mas_antiguo():
    """Devuelve el pendiente más viejo (el próximo a enviar) como dict con
    claves id/codigo/origen/fecha_hora/intentos, o None si no hay
    ninguno pendiente."""
    with _lock:
        fila = _conexion.execute(
            "SELECT id, codigo, origen, fecha_hora, intentos FROM pendientes "
            "ORDER BY id ASC LIMIT 1"
        ).fetchone()
    if not fila:
        return None
    id_, codigo, origen, fecha_hora, intentos = fila
    return {
        "id": id_,
        "codigo": codigo,
        "origen": origen,
        "fecha_hora": datetime.fromisoformat(fecha_hora),
        "intentos": intentos,
    }


def marcar_intento_fallido(id_):
    with _lock:
        _conexion.execute(
            "UPDATE pendientes SET intentos = intentos + 1 WHERE id = ?", (id_,)
        )
        _conexion.commit()


def eliminar(id_):
    with _lock:
        _conexion.execute("DELETE FROM pendientes WHERE id = ?", (id_,))
        _conexion.commit()


def contar_pendientes():
    with _lock:
        (total,) = _conexion.execute("SELECT COUNT(*) FROM pendientes").fetchone()
    return total
