"""
Lógica compartida entre los dos terminales del proyecto:

- `leer_qr.py`            -> terminal de prueba en PC (cámara USB/webcam)
- `leer_qr_raspberry.py`  -> terminal de producción en Raspberry Pi
                              (cámara del módulo Raspberry + lector QR
                              USB de mesa WD-1012, los dos a la vez)

Se centraliza acá todo lo que NO depende de qué hardware está leyendo el
QR: hablar con el backend, decidir el color/mensaje del banner, el latido
(heartbeat), y el apagado remoto. Así los dos scripts nunca pueden
"desincronizarse" en cómo hablan con el backend -- si el contrato de la
API cambia, solo hay que tocar este archivo.

Ninguno de los dos terminales toca la base de datos ni AcademicOK
directamente -- solo llaman a POST /api/acceso y muestran el resultado
(ver sección 11 del documento técnico: "la Raspberry no debe acceder
directamente a la base de datos").
"""
import os
import platform
import subprocess
import threading
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
PUNTO_ACCESO_ID = int(os.getenv("PUNTO_ACCESO_ID", "1"))
TIEMPO_ANTIDUPLICADO = float(os.getenv("TIEMPO_ANTIDUPLICADO", "5"))
INTERVALO_LATIDO = float(os.getenv("INTERVALO_LATIDO", "15"))

# Colores en BGR (formato que usa OpenCV, no RGB)
COLOR_MARCA = (173, 158, 0)     # #009EAD (color institucional)
COLOR_ENTRADA = (60, 160, 60)   # verde
COLOR_SALIDA = (0, 170, 220)    # ámbar
COLOR_DENEGADO = (50, 50, 220)  # rojo
COLOR_ERROR = (90, 90, 90)      # gris

BANNER_DURACION = 4.0  # segundos que se muestra el resultado en pantalla

# Se pone en True cuando llega la orden de apagar desde el panel; el bucle
# principal de cada terminal lo revisa para cerrarse solo, y main() apaga
# el equipo al salir.
apagar_solicitado = threading.Event()


# --------------------------------------------------------------------------
# Comunicación con el backend
# --------------------------------------------------------------------------
def registrar_acceso(qr_texto):
    """Llama a POST /api/acceso en el backend. Devuelve (ok: bool, data: dict)."""
    try:
        respuesta = requests.post(
            f"{API_URL}/api/acceso",
            json={"qr": qr_texto, "punto_acceso": PUNTO_ACCESO_ID},
            timeout=8,
        )
        if respuesta.status_code == 200:
            return True, respuesta.json()
        return False, {
            "mensaje": f"El backend respondió {respuesta.status_code}: {respuesta.text}"
        }
    except requests.RequestException as error:
        return False, {"mensaje": f"No se pudo contactar al backend: {error}"}


def color_para(resultado):
    return {
        "ENTRADA": COLOR_ENTRADA,
        "SALIDA": COLOR_SALIDA,
        "DENEGADO": COLOR_DENEGADO,
    }.get(resultado, COLOR_ERROR)


def procesar_qr(datos, origen="cámara"):
    """Consulta el backend y arma el (titulo, subtitulo, color) del banner.
    `origen` es solo para el log de consola ("cámara" o "lector USB"), útil
    para distinguir cuál de los dos detectó el código en la Raspberry."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] QR detectado ({origen}), consultando backend...")

    ok, data = registrar_acceso(datos)

    if not ok:
        print("  ->", data["mensaje"])
        return "ERROR DE CONEXIÓN", data["mensaje"], COLOR_ERROR

    resultado = data.get("resultado", "DENEGADO")
    persona = data.get("persona")
    nombre = None
    if persona:
        nombre = " ".join(
            parte for parte in [persona.get("nombres"), persona.get("apellidos")] if parte
        )

    mensaje = data.get("mensaje", "")
    print(f"  -> {resultado}: {nombre or '(sin persona)'} — {mensaje}")

    if resultado == "ENTRADA":
        titulo = "✓ ENTRADA REGISTRADA"
    elif resultado == "SALIDA":
        titulo = "✓ SALIDA REGISTRADA"
    else:
        titulo = "✗ ACCESO DENEGADO"

    subtitulo = nombre or mensaje or "—"
    return titulo, subtitulo, color_para(resultado)


# --------------------------------------------------------------------------
# Control de duplicados -- pensado para poder usarse desde dos hilos a la
# vez (cámara + lector USB) sin registrar el mismo QR dos veces si ambos
# lo detectan casi al mismo tiempo.
# --------------------------------------------------------------------------
class ControlDuplicados:
    def __init__(self, ventana_segundos=TIEMPO_ANTIDUPLICADO):
        self.ventana = ventana_segundos
        self._lock = threading.Lock()
        self._ultimo_codigo = None
        self._ultimo_momento = 0.0

    def deberia_procesar(self, codigo):
        ahora = time.time()
        with self._lock:
            es_nuevo = (
                codigo != self._ultimo_codigo
                or (ahora - self._ultimo_momento) > self.ventana
            )
            if es_nuevo:
                self._ultimo_codigo = codigo
                self._ultimo_momento = ahora
            return es_nuevo

    def reiniciar(self):
        with self._lock:
            self._ultimo_codigo = None


# --------------------------------------------------------------------------
# Estado del banner en pantalla -- también pensado para que lo actualice
# cualquiera de los dos hilos y lo lea el hilo que dibuja la ventana.
# --------------------------------------------------------------------------
class EstadoBanner:
    def __init__(self, duracion=BANNER_DURACION):
        self.duracion = duracion
        self._lock = threading.Lock()
        self._banner = None
        self._hasta = 0.0

    def mostrar(self, titulo, subtitulo, color):
        with self._lock:
            self._banner = (titulo, subtitulo, color)
            self._hasta = time.time() + self.duracion

    def actual(self):
        with self._lock:
            if self._banner and time.time() < self._hasta:
                return self._banner
            return None


# --------------------------------------------------------------------------
# Latido (heartbeat) y apagado remoto
# --------------------------------------------------------------------------
def enviar_latido():
    """
    Avisa al backend que este terminal sigue encendido (POST
    /api/puntos-acceso/{id}/latido) y devuelve el comando pendiente que
    haya dejado el panel, si hay alguno (hoy solo "APAGAR").
    """
    try:
        respuesta = requests.post(
            f"{API_URL}/api/puntos-acceso/{PUNTO_ACCESO_ID}/latido", timeout=6
        )
        if respuesta.status_code == 200:
            return respuesta.json().get("comando")
    except requests.RequestException:
        pass  # sin red o backend caído: se reintenta en el próximo latido
    return None


def hilo_latido():
    """Corre en segundo plano mientras dura el programa, mandando un
    latido cada INTERVALO_LATIDO segundos y revisando si el panel pidió
    apagar el equipo."""
    while not apagar_solicitado.is_set():
        comando = enviar_latido()
        if comando == "APAGAR":
            print("Se recibió orden de apagar desde el panel.")
            apagar_solicitado.set()
            break
        apagar_solicitado.wait(INTERVALO_LATIDO)


def apagar_equipo():
    """Apaga el equipo donde corre este terminal.

    - Windows (la PC de pruebas): `shutdown /s /t 5` -- apaga toda la PC,
      no solo el script.
    - Linux / Raspberry Pi OS: `sudo shutdown -h now`. El usuario que
      corre el script necesita permiso para apagar sin contraseña --
      ver README_RASPBERRY.md, sección de sudoers (NOPASSWD para
      /sbin/shutdown). Ya NO se asume que el usuario se llama "pi": las
      imágenes recientes de Raspberry Pi OS piden elegir el nombre de
      usuario al grabar la SD.
    """
    print("Apagando el equipo...")
    try:
        if platform.system() == "Windows":
            subprocess.run(["shutdown", "/s", "/t", "5"], check=False)
        else:
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)
    except Exception as error:
        print(f"No se pudo apagar el equipo automáticamente: {error}")
        print("Apágalo manualmente.")
