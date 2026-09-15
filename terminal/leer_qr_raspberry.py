"""
Terminal de producción para Raspberry Pi.

A diferencia de `leer_qr.py` (terminal de prueba en PC, con una cámara
USB/webcam), este script lee el QR de DOS formas a la vez, cualquiera de
las dos puede registrar el acceso:

1. La **cámara del módulo Raspberry** (CSI, vía `picamera2`), decodificando
   el QR de la imagen con el mismo detector de OpenCV ya validado en el
   terminal de PC.
2. El **lector QR/barras USB de mesa** (WD-1012 u otro "keyboard wedge"),
   leído directamente del dispositivo de entrada de Linux (`evdev`) --
   ver `escaner_teclado.py`.

Ambos caminos llaman a la misma lógica compartida (`comun.py`): consultan
el backend, arman el banner de resultado, y comparten el control de
duplicados para no registrar el mismo QR dos veces si ambos lo detectan
casi al mismo tiempo (por ejemplo, si alguien lo escanea con el lector de
mesa justo cuando también queda encuadrado por la cámara).

Requisitos (ver README_RASPBERRY.md para la guía completa paso a paso):
    - picamera2 y opencv (se instalan con apt, no con pip, en Raspberry
      Pi OS -- ver README_RASPBERRY.md)
    - pip install -r requirements-raspberry.txt   (evdev, requests, etc.)
    - el backend accesible en la red (ver .env)
    - el lector USB conectado y su ruta configurada en .env
      (SCANNER_DEVICE_PATH)

Uso:
    python3 leer_qr_raspberry.py

Controles (con teclado conectado; en producción no hace falta ninguno):
    ESC  -> salir
    R    -> forzar una nueva lectura del mismo QR
"""
import os
import threading

import cv2
from dotenv import load_dotenv

import comun
from escaner_teclado import LectorTecladoUSB

load_dotenv()

try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None

RESOLUCION_CAMARA = (
    int(os.getenv("CAMARA_ANCHO", "640")),
    int(os.getenv("CAMARA_ALTO", "480")),
)
PANTALLA_COMPLETA = os.getenv("PANTALLA_COMPLETA", "false").lower() == "true"
SCANNER_DEVICE_PATH = os.getenv("SCANNER_DEVICE_PATH", "").strip()

NOMBRE_VENTANA = "Control de Acceso"


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


def main():
    if Picamera2 is None:
        print(
            "No se encontró 'picamera2'. En Raspberry Pi OS se instala con:\n"
            "  sudo apt install -y python3-picamera2\n"
            "Ver README_RASPBERRY.md."
        )
        return

    control_duplicados = comun.ControlDuplicados()
    estado_banner = comun.EstadoBanner()

    def al_detectar(codigo, origen):
        if not control_duplicados.deberia_procesar(codigo):
            return
        titulo, subtitulo, color = comun.procesar_qr(codigo, origen=origen)
        estado_banner.mostrar(titulo, subtitulo, color)

    # --- Lector USB de mesa (WD-1012), en su propio hilo ---
    lector_usb = None
    if SCANNER_DEVICE_PATH:
        lector_usb = LectorTecladoUSB(
            SCANNER_DEVICE_PATH,
            al_completar_codigo=lambda codigo: al_detectar(codigo, origen="lector USB"),
        )
        lector_usb.iniciar()
    else:
        print(
            "[aviso] SCANNER_DEVICE_PATH no está configurado en .env -- el "
            "lector QR de mesa no va a estar activo, solo la cámara. Ver "
            "README_RASPBERRY.md para encontrar la ruta del dispositivo."
        )

    # --- Latido / apagado remoto, igual que en el terminal de PC ---
    hilo_de_latido = threading.Thread(target=comun.hilo_latido, daemon=True)
    hilo_de_latido.start()

    # --- Cámara del módulo Raspberry ---
    picam2 = Picamera2()
    configuracion = picam2.create_preview_configuration(
        main={"format": "BGR888", "size": RESOLUCION_CAMARA}
    )
    picam2.configure(configuracion)
    picam2.start()

    detector = cv2.QRCodeDetector()

    cv2.namedWindow(NOMBRE_VENTANA, cv2.WINDOW_NORMAL)
    if PANTALLA_COMPLETA:
        cv2.setWindowProperty(
            NOMBRE_VENTANA, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )

    print("========================================")
    print("   CONTROL DE ACCESO - TERMINAL (Raspberry Pi)")
    print("========================================")
    print(f"Backend: {comun.API_URL}")
    print(f"Punto de acceso: {comun.PUNTO_ACCESO_ID}")
    print(f"Lector USB: {SCANNER_DEVICE_PATH or '(no configurado)'}")
    print()
    print("Muestre el código QR frente a la cámara, o escanéelo con el lector de mesa.")
    print("R = volver a escanear   ESC = salir")
    print()

    try:
        while not comun.apagar_solicitado.is_set():
            frame = picam2.capture_array()

            datos, puntos, _ = detector.detectAndDecode(frame)
            if datos:
                al_detectar(datos, origen="cámara")

            if puntos is not None:
                puntos_enteros = puntos.astype(int)
                for i in range(4):
                    p1 = tuple(puntos_enteros[0][i])
                    p2 = tuple(puntos_enteros[0][(i + 1) % 4])
                    cv2.line(frame, p1, p2, (0, 255, 0), 3)

            banner = estado_banner.actual()
            if banner:
                dibujar_banner(frame, banner[0], banner[1], banner[2])
            else:
                dibujar_banner(
                    frame, "CONTROL DE ACCESO",
                    "Acerque su QR a la cámara o al lector de mesa",
                    comun.COLOR_MARCA,
                )

            if comun.apagar_solicitado.is_set():
                dibujar_banner(
                    frame, "APAGANDO EL EQUIPO...",
                    "Orden recibida desde el panel", comun.COLOR_DENEGADO,
                )

            cv2.imshow(NOMBRE_VENTANA, frame)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla == 27:  # ESC
                break
            if tecla == ord("r"):
                control_duplicados.reiniciar()
                print("Listo para nuevo escaneo.")

            if comun.apagar_solicitado.is_set():
                cv2.waitKey(1500)
                break
    finally:
        if lector_usb:
            lector_usb.detener()
        picam2.stop()
        cv2.destroyAllWindows()

    if comun.apagar_solicitado.is_set():
        comun.apagar_equipo()


if __name__ == "__main__":
    main()
