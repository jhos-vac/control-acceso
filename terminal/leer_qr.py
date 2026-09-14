"""
Terminal de prueba (PC) para el control de acceso por QR.

Lee el QR con la cámara y lo envía al backend (POST /api/acceso). El
backend es quien decide todo: si la persona ya existe localmente, si
hay que consultarla en AcademicOK, y si corresponde ENTRADA, SALIDA o
acceso DENEGADO. Este script NO toca la base de datos ni AcademicOK
directamente — solo lee el QR y muestra el resultado, igual que hará
la Raspberry Pi en producción (ver sección 11 del documento técnico:
"la Raspberry no debe acceder directamente a la base de datos").

Requisitos:
    pip install -r requirements.txt
    (y el backend corriendo, ver ../backend/README.md)

Uso:
    python leer_qr.py

Controles:
    ESC  -> salir
    R    -> forzar una nueva lectura del mismo QR (por si se quiere
            volver a escanear antes de que pase el tiempo antiduplicado)
"""
import os
import platform
import subprocess
import threading
import time
from datetime import datetime

import cv2
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
PUNTO_ACCESO_ID = int(os.getenv("PUNTO_ACCESO_ID", "1"))
CAMARA_INDICE = int(os.getenv("CAMARA_INDICE", "0"))
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
# principal de la cámara lo revisa para cerrarse solo, y main() apaga el
# equipo al salir.
apagar_solicitado = threading.Event()


def registrar_acceso(qr_texto):
    """
    Llama a POST /api/acceso en el backend.
    Devuelve (ok: bool, data: dict).
    """
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


def dibujar_banner(frame, titulo, subtitulo, color):
    alto, ancho = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (ancho, 90), color, -1)
    cv2.putText(
        frame, titulo, (20, 38),
        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA,
    )
    cv2.putText(
        frame, subtitulo[:80], (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1, cv2.LINE_AA,
    )


def procesar_qr(datos):
    """Consulta el backend y arma el (titulo, subtitulo, color) del banner."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] QR detectado, consultando backend...")

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
    """Apaga el equipo donde corre este terminal. En Windows (la PC de
    pruebas actual) apaga toda la PC, no solo este script — ver aviso en
    el panel antes de usarlo. En Linux (pensado para la Raspberry Pi más
    adelante) requiere permiso de apagado sin contraseña para el usuario
    que corre el script (sudoers con NOPASSWD para /sbin/shutdown)."""
    print("Apagando el equipo...")
    try:
        if platform.system() == "Windows":
            subprocess.run(["shutdown", "/s", "/t", "5"], check=False)
        else:
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)
    except Exception as error:
        print(f"No se pudo apagar el equipo automáticamente: {error}")
        print("Apágalo manualmente.")


def main():
    cap = cv2.VideoCapture(CAMARA_INDICE)
    if not cap.isOpened():
        print("No se pudo abrir la cámara.")
        return

    detector = cv2.QRCodeDetector()

    ultimo_qr = None
    ultimo_escaneo = 0.0

    banner = None
    banner_hasta = 0.0

    print("========================================")
    print("   CONTROL DE ACCESO - TERMINAL (PC)")
    print("========================================")
    print(f"Backend: {API_URL}")
    print(f"Punto de acceso: {PUNTO_ACCESO_ID}")
    print()
    print("Muestre el código QR frente a la cámara.")
    print("R = volver a escanear   ESC = salir")
    print()

    hilo = threading.Thread(target=hilo_latido, daemon=True)
    hilo.start()

    while not apagar_solicitado.is_set():
        ret, frame = cap.read()
        if not ret:
            print("No se pudo obtener imagen de la cámara.")
            break

        datos, puntos, _ = detector.detectAndDecode(frame)

        if datos:
            ahora = time.time()
            puede_procesar = (
                datos != ultimo_qr or (ahora - ultimo_escaneo) > TIEMPO_ANTIDUPLICADO
            )

            if puede_procesar:
                ultimo_qr = datos
                ultimo_escaneo = ahora

                titulo, subtitulo, color = procesar_qr(datos)
                banner = (titulo, subtitulo, color)
                banner_hasta = time.time() + BANNER_DURACION

        if puntos is not None:
            puntos = puntos.astype(int)
            for i in range(4):
                p1 = tuple(puntos[0][i])
                p2 = tuple(puntos[0][(i + 1) % 4])
                cv2.line(frame, p1, p2, (0, 255, 0), 3)

        if banner and time.time() < banner_hasta:
            dibujar_banner(frame, banner[0], banner[1], banner[2])
        else:
            dibujar_banner(
                frame, "CONTROL DE ACCESO", "Acerque su código QR a la cámara", COLOR_MARCA
            )

        if apagar_solicitado.is_set():
            dibujar_banner(
                frame, "APAGANDO EL EQUIPO...", "Orden recibida desde el panel", COLOR_DENEGADO
            )

        cv2.imshow("Control de Acceso - Escanee QR", frame)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == 27:  # ESC
            break
        if tecla == ord("r"):
            ultimo_qr = None
            print("Listo para nuevo escaneo.")

        if apagar_solicitado.is_set():
            cv2.waitKey(1500)  # deja un instante el aviso en pantalla antes de cerrar
            break

    cap.release()
    cv2.destroyAllWindows()

    if apagar_solicitado.is_set():
        apagar_equipo()


if __name__ == "__main__":
    main()
