"""
Terminal de prueba (PC) para el control de acceso por QR.

Lee el QR con la cámara y lo envía al backend (POST /api/acceso). El
backend es quien decide todo: si la persona ya existe localmente, si
hay que consultarla en AcademicOK, y si corresponde ENTRADA, SALIDA o
acceso DENEGADO. Este script NO toca la base de datos ni AcademicOK
directamente — solo lee el QR y muestra el resultado.

Para el terminal de producción en Raspberry Pi (cámara del módulo +
lector QR USB de mesa a la vez), ver `leer_qr_raspberry.py` y
`README_RASPBERRY.md`. La lógica de comunicación con el backend
(latido, apagado remoto, armado del banner) vive en `comun.py` y la
comparten los dos scripts.

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
import threading
import time

import cv2
from dotenv import load_dotenv

import comun

load_dotenv()

CAMARA_INDICE = int(os.getenv("CAMARA_INDICE", "0"))


def main():
    cap = cv2.VideoCapture(CAMARA_INDICE)
    if not cap.isOpened():
        print("No se pudo abrir la cámara.")
        return

    detector = cv2.QRCodeDetector()
    control_duplicados = comun.ControlDuplicados()

    banner = None
    banner_hasta = 0.0

    print("========================================")
    print("   CONTROL DE ACCESO - TERMINAL (PC)")
    print("========================================")
    print(f"Backend: {comun.API_URL}")
    print(f"Punto de acceso: {comun.PUNTO_ACCESO_ID}")
    print()
    print("Muestre el código QR frente a la cámara.")
    print("R = volver a escanear   ESC = salir")
    print()

    hilo = threading.Thread(target=comun.hilo_latido, daemon=True)
    hilo.start()

    while not comun.apagar_solicitado.is_set():
        ret, frame = cap.read()
        if not ret:
            print("No se pudo obtener imagen de la cámara.")
            break

        datos, puntos, _ = detector.detectAndDecode(frame)

        if datos and control_duplicados.deberia_procesar(datos):
            titulo, subtitulo, color = comun.procesar_qr(datos)
            banner = (titulo, subtitulo, color)
            banner_hasta = time.time() + comun.BANNER_DURACION

        if puntos is not None:
            puntos = puntos.astype(int)
            for i in range(4):
                p1 = tuple(puntos[0][i])
                p2 = tuple(puntos[0][(i + 1) % 4])
                cv2.line(frame, p1, p2, (0, 255, 0), 3)

        if banner and time.time() < banner_hasta:
            _dibujar_banner(frame, banner[0], banner[1], banner[2])
        else:
            _dibujar_banner(
                frame, "CONTROL DE ACCESO", "Acerque su código QR a la cámara", comun.COLOR_MARCA
            )

        if comun.apagar_solicitado.is_set():
            _dibujar_banner(
                frame, "APAGANDO EL EQUIPO...", "Orden recibida desde el panel", comun.COLOR_DENEGADO
            )

        cv2.imshow("Control de Acceso - Escanee QR", frame)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == 27:  # ESC
            break
        if tecla == ord("r"):
            control_duplicados.reiniciar()
            print("Listo para nuevo escaneo.")

        if comun.apagar_solicitado.is_set():
            cv2.waitKey(1500)  # deja un instante el aviso en pantalla antes de cerrar
            break

    cap.release()
    cv2.destroyAllWindows()

    if comun.apagar_solicitado.is_set():
        comun.apagar_equipo()


def _dibujar_banner(frame, titulo, subtitulo, color):
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


if __name__ == "__main__":
    main()
