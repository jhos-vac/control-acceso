"""
Terminal de producción para Raspberry Pi — SOLO lector QR/barras USB de
mesa (WD-1012 u otro "keyboard wedge"). No usa cámara.

(Nota: una versión anterior de este script también leía QR con la cámara
del módulo Raspberry a la vez que con el lector USB. Se quitó esa parte
a pedido del usuario para simplificar -- si en algún momento hace falta
recuperarla, la lógica de cámara vivía en un hilo aparte que llamaba a
`comun.procesar_qr()` igual que el lector USB, así que se puede volver a
agregar sin tocar el resto.)

El lector USB se lee directamente del dispositivo de entrada de Linux
(`evdev`, ver `escaner_teclado.py`) en un hilo aparte -- no depende de que
ninguna ventana tenga el foco del teclado, algo esencial en un kiosco.

Como ya no hay imagen de cámara que mostrar, la pantalla es simple:
un color de fondo + título + subtítulo (con Tkinter, que viene con
Python -- no hace falta instalar OpenCV para esto).

Cada código leído se guarda de inmediato en una cola local en disco
(`cola_local.py`, SQLite) y se sigue leyendo sin esperar nada -- un hilo
aparte (`comun.hilo_envio`) los manda al backend uno por uno, en el
mismo orden en que se leyeron. Esto resuelve dos cosas que pidió el
usuario:
  - **Velocidad**: con afluencia de gente, cada persona solo espera lo
    que tarda el lector en leer el código (1-2 segundos), no lo que
    tarde la red/backend en responder.
  - **Sin conexión**: si se cae la red o el backend, nada se pierde --
    los códigos quedan pendientes en el archivo `cola_local.db` (sobrevive
    un reinicio) hasta que vuelva la conexión, momento en que se mandan
    solos en orden.

Además, si la misma persona escanea dos veces en menos de
`MINUTOS_ANTIDUPLICADO_MOVIMIENTO` (configurado en el backend, no acá),
el backend responde "DUPLICADO" en vez de alternar ENTRADA/SALIDA -- se
muestra en un color distinto (púrpura) para que se note.

Autonomía / red WiFi (ver `red.py`): un hilo en segundo plano
(`hilo_red`) revisa cada pocos segundos si el dispositivo tiene alguna
red activa. Si no la tiene, la pantalla de espera avisa "SIN CONEXIÓN
WIFI" y ofrece dos salidas, sin necesitar teclado ni mouse:
  - Escanear un código QR de WiFi (el mismo tipo que genera cualquier
    router, o que se comparte desde un celular) con el mismo lector USB
    -- el terminal detecta que no es un QR de credencial y en cambio
    intenta conectarse a esa red con `nmcli`.
  - Tocar el botón en pantalla "Continuar sin conexión" (la pantalla es
    táctil) -- el terminal sigue funcionando igual, guardando todo en la
    cola local hasta que haya red.
Esto, junto con el arranque automático (ver README_RASPBERRY.md,
"Autonomía: instalación con un solo script" y "Arranque automático"),
es lo que permite que baste con encender el dispositivo para que
funcione solo, sin depender de que alguien lo conecte a un teclado o
revise si tiene red.

Requisitos (ver README_RASPBERRY.md para la guía completa paso a paso):
    - Python con Tkinter (`sudo apt install -y python3-tk`, si no
      viniera ya instalado)
    - pip install -r requirements-raspberry.txt   (evdev, requests, etc.)
    - el backend accesible en la red (ver .env)
    - el lector USB conectado y su ruta configurada en .env
      (SCANNER_DEVICE_PATH)
    - NetworkManager (`nmcli`) con permiso de sudo sin contraseña, para
      poder conectar a una red WiFi nueva (ver README_RASPBERRY.md)

Uso:
    python3 leer_qr_raspberry.py

Controles:
    ESC  -> salir (cierra la ventana; NO apaga el equipo -- el apagado
            remoto solo lo dispara una orden real del panel)
"""
import os
import queue
import threading
import tkinter as tk

from dotenv import load_dotenv

import cola_local
import comun
import red
from escaner_teclado import LectorTecladoUSB

load_dotenv()

PANTALLA_COMPLETA = os.getenv("PANTALLA_COMPLETA", "false").lower() == "true"
SCANNER_DEVICE_PATH = os.getenv("SCANNER_DEVICE_PATH", "").strip()
REVISAR_RED_SEGUNDOS = float(os.getenv("REVISAR_RED_SEGUNDOS", "5"))

# Cada cuántos milisegundos la ventana revisa si el lector USB dejó un
# código nuevo en la cola, o si llegó una orden de apagado.
REVISAR_COLA_MS = 150

TITULO_IDLE = "CONTROL DE ACCESO"
SUBTITULO_IDLE = "Acerque su código QR al lector"

TITULO_SIN_RED = "SIN CONEXIÓN WIFI"
SUBTITULO_SIN_RED = (
    "Escanee un código QR de WiFi para conectarse, o toque el botón "
    "para continuar sin conexión"
)


def _color_hex(color_bgr):
    """comun.py define los colores en BGR (por herencia de OpenCV);
    Tkinter necesita un string tipo "#RRGGBB"."""
    azul, verde, rojo = color_bgr
    return f"#{rojo:02x}{verde:02x}{azul:02x}"


class VentanaTerminal:
    """Pantalla de kiosco simple: un color de fondo + título + subtítulo.
    Sin cámara -- solo refleja el resultado de cada lectura del QR (y,
    cuando no hay red, ofrece un botón táctil para continuar offline)."""

    FUENTE_TITULO = ("DejaVu Sans", 42, "bold")
    FUENTE_SUBTITULO = ("DejaVu Sans", 20)
    FUENTE_BOTON = ("DejaVu Sans", 16)

    def __init__(self, root, pantalla_completa, al_continuar_sin_conexion):
        self.root = root
        root.title("Control de Acceso")

        if pantalla_completa:
            root.attributes("-fullscreen", True)
            root.config(cursor="none")
        else:
            root.geometry("800x480")

        root.bind("<Escape>", lambda _evento: root.destroy())

        # True mientras no se detecta ninguna red -- decide qué muestra
        # mostrar_idle() (ver establecer_estado_red()). Lo actualiza
        # hilo_red() a través de _drenar_estado_red().
        self.sin_red = False

        color_inicial = _color_hex(comun.COLOR_MARCA)
        self._marco = tk.Frame(root, bg=color_inicial)
        self._marco.pack(fill="both", expand=True)

        self.titulo_var = tk.StringVar(value=TITULO_IDLE)
        self.subtitulo_var = tk.StringVar(value=SUBTITULO_IDLE)

        self._label_titulo = tk.Label(
            self._marco, textvariable=self.titulo_var, font=self.FUENTE_TITULO,
            fg="white", bg=color_inicial, wraplength=760, justify="center",
        )
        self._label_titulo.pack(expand=True)

        self._label_subtitulo = tk.Label(
            self._marco, textvariable=self.subtitulo_var, font=self.FUENTE_SUBTITULO,
            fg="white", bg=color_inicial, wraplength=760, justify="center",
        )
        self._label_subtitulo.pack(pady=(0, 20))

        # Botón táctil "Continuar sin conexión" -- solo se empaqueta
        # (se hace visible) cuando la pantalla de espera está en el
        # estado "sin red" (ver mostrar_idle()); en cualquier otro
        # momento queda oculto.
        self._boton_sin_conexion = tk.Button(
            self._marco, text="Continuar sin conexión", font=self.FUENTE_BOTON,
            command=al_continuar_sin_conexion,
        )

    def establecer_estado_red(self, conectado):
        self.sin_red = not conectado

    def mostrar(self, titulo, subtitulo, color_bgr):
        self._boton_sin_conexion.pack_forget()
        color = _color_hex(color_bgr)
        self._marco.configure(bg=color)
        self._label_titulo.configure(bg=color)
        self._label_subtitulo.configure(bg=color)
        self.titulo_var.set(titulo)
        self.subtitulo_var.set(subtitulo)

    def mostrar_idle(self):
        if self.sin_red:
            self.mostrar(TITULO_SIN_RED, SUBTITULO_SIN_RED, comun.COLOR_ERROR)
            self._boton_sin_conexion.pack(pady=(0, 30))
        else:
            self.mostrar(TITULO_IDLE, SUBTITULO_IDLE, comun.COLOR_MARCA)


def _drenar_cola(cola_codigos, control_duplicados, ventana, cola_wifi):
    """Saca todos los códigos que haya dejado el lector USB en la cola
    (`cola_codigos`, en memoria -- solo dura mientras el programa corre).
    Si un código tiene pinta de ser un QR de WiFi (`red.es_codigo_wifi`),
    lo manda a `cola_wifi` para que `hilo_red()` intente conectarse (no
    se procesa acá para no bloquear la ventana esperando a `nmcli`, que
    puede tardar varios segundos). Cualquier otro código se guarda en la
    cola local persistente (`cola_local`, en disco) para que
    `comun.hilo_envio()` lo mande al backend en otro hilo -- NO espera
    respuesta del backend acá, para no frenar la siguiente lectura.
    Muestra de inmediato un aviso de "leído" para cada uno. Devuelve True
    si se mostró algo nuevo. Separado de `main()` para poder probarlo sin
    necesitar una ventana real."""
    se_mostro_algo = False
    while True:
        try:
            codigo = cola_codigos.get_nowait()
        except queue.Empty:
            break
        if not control_duplicados.deberia_procesar(codigo):
            continue
        if red.es_codigo_wifi(codigo):
            cola_wifi.put(codigo)
            ventana.mostrar("Código WiFi leído", "Conectando...", comun.COLOR_MARCA)
        else:
            comun.encolar_qr(codigo, origen="lector USB")
            ventana.mostrar("Código leído", "Registrando...", comun.COLOR_MARCA)
        se_mostro_algo = True
    return se_mostro_algo


def _drenar_resultados(cola_resultados, ventana):
    """Saca los resultados que haya dejado `comun.hilo_envio()` (el hilo
    que manda los pendientes al backend, en segundo plano) y actualiza la
    ventana con el más reciente. Separado de `_drenar_cola()` porque
    llegan de un hilo distinto, en un momento distinto (la red puede
    demorar) -- así la lectura del QR nunca queda bloqueada esperando
    esto. Devuelve True si se mostró algo nuevo."""
    se_mostro_algo = False
    while True:
        try:
            titulo, subtitulo, color = cola_resultados.get_nowait()
        except queue.Empty:
            break
        ventana.mostrar(titulo, subtitulo, color)
        se_mostro_algo = True
    return se_mostro_algo


def _drenar_estado_red(cola_estado_red, ventana):
    """Saca los avisos que deja `hilo_red()` (cambios de conectado/sin
    red, o el resultado de intentar conectarse a una red WiFi nueva) y
    actualiza la ventana. Devuelve True si se mostró algo nuevo."""
    se_mostro_algo = False
    while True:
        try:
            evento = cola_estado_red.get_nowait()
        except queue.Empty:
            break
        tipo = evento["tipo"]
        if tipo == "conectado":
            ventana.establecer_estado_red(True)
            ventana.mostrar_idle()
        elif tipo == "sin_red":
            ventana.establecer_estado_red(False)
            ventana.mostrar_idle()
        elif tipo == "conectando":
            ventana.mostrar("Conectando a WiFi...", evento["ssid"], comun.COLOR_MARCA)
        elif tipo == "conexion_exitosa":
            ventana.establecer_estado_red(True)
            ventana.mostrar("✓ CONECTADO", evento["ssid"], comun.COLOR_ENTRADA)
        elif tipo == "conexion_fallida":
            ventana.mostrar("✗ NO SE PUDO CONECTAR", evento["mensaje"], comun.COLOR_DENEGADO)
        se_mostro_algo = True
    return se_mostro_algo


def hilo_red(cola_wifi, cola_estado_red):
    """Corre en segundo plano todo el tiempo: revisa cada
    REVISAR_RED_SEGUNDOS si el dispositivo tiene alguna red activa
    (`red.hay_red()`) y avisa por `cola_estado_red` solo cuando el estado
    CAMBIA (no en cada revisión, para no redibujar la pantalla sin
    necesidad). También procesa lo que deje `cola_wifi` (códigos QR de
    WiFi detectados por `_drenar_cola()`): intenta conectarse con
    `red.conectar_wifi()` y avisa el resultado -- esto puede tardar unos
    segundos (nmcli conectándose), por eso corre en su propio hilo y no
    bloquea la ventana."""
    conectado_antes = None
    while not comun.apagar_solicitado.is_set():
        try:
            codigo_wifi = cola_wifi.get_nowait()
        except queue.Empty:
            codigo_wifi = None

        if codigo_wifi:
            datos = red.parsear_codigo_wifi(codigo_wifi)
            if datos:
                cola_estado_red.put({"tipo": "conectando", "ssid": datos["ssid"]})
                ok, mensaje = red.conectar_wifi(datos["ssid"], datos["password"], datos["tipo"])
                if ok:
                    print(f"[red] Conectado a '{datos['ssid']}'")
                    cola_estado_red.put({"tipo": "conexion_exitosa", "ssid": datos["ssid"]})
                    conectado_antes = True
                else:
                    print(f"[red] No se pudo conectar a '{datos['ssid']}': {mensaje}")
                    cola_estado_red.put({"tipo": "conexion_fallida", "mensaje": mensaje})
            continue  # revisar de nuevo enseguida en vez de esperar el intervalo normal

        conectado_ahora = red.hay_red()
        if conectado_ahora != conectado_antes:
            cola_estado_red.put({"tipo": "conectado" if conectado_ahora else "sin_red"})
            conectado_antes = conectado_ahora

        comun.apagar_solicitado.wait(REVISAR_RED_SEGUNDOS)


def main():
    if not SCANNER_DEVICE_PATH:
        print(
            "SCANNER_DEVICE_PATH no está configurado en .env -- sin él no hay "
            "forma de leer el QR (este terminal ya no usa cámara). Ver "
            "README_RASPBERRY.md, sección 'Encontrar la ruta del lector USB'."
        )
        return

    cola_codigos = queue.Queue()      # lector USB -> _drenar_cola (en memoria)
    cola_resultados = queue.Queue()   # hilo_envio -> _drenar_resultados (en memoria)
    cola_wifi = queue.Queue()         # _drenar_cola -> hilo_red (en memoria)
    cola_estado_red = queue.Queue()   # hilo_red -> _drenar_estado_red (en memoria)
    control_duplicados = comun.ControlDuplicados()

    lector_usb = LectorTecladoUSB(SCANNER_DEVICE_PATH, al_completar_codigo=cola_codigos.put)
    lector_usb.iniciar()

    hilo_de_latido = threading.Thread(target=comun.hilo_latido, daemon=True)
    hilo_de_latido.start()

    hilo_de_envio = threading.Thread(
        target=comun.hilo_envio, args=(cola_resultados,), daemon=True
    )
    hilo_de_envio.start()

    hilo_de_red = threading.Thread(
        target=hilo_red, args=(cola_wifi, cola_estado_red), daemon=True
    )
    hilo_de_red.start()

    print("========================================")
    print("   CONTROL DE ACCESO - TERMINAL (Raspberry Pi)")
    print("========================================")
    print(f"Backend: {comun.API_URL}")
    print(f"Punto de acceso: {comun.PUNTO_ACCESO_ID}")
    print(f"Lector USB: {SCANNER_DEVICE_PATH}")
    pendientes_al_iniciar = cola_local.contar_pendientes()
    if pendientes_al_iniciar:
        print(
            f"Hay {pendientes_al_iniciar} lectura(s) pendiente(s) de un arranque "
            "anterior (quedaron guardadas sin conexión) -- se van a enviar solas."
        )
    print()
    print("Escanee un código QR con el lector de mesa.")
    print("ESC = salir")
    print()

    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(
            f"No se pudo abrir la ventana del terminal (Tkinter): {error}\n"
            "Esto casi siempre pasa al correr el script por SSH sin que "
            "haya una sesión de escritorio activa en la Raspberry (no hay "
            "variable DISPLAY). Si el escritorio SÍ está abierto en la "
            "pantalla de la Raspberry, probá anteponiendo la variable "
            "DISPLAY, por ejemplo:\n"
            "  DISPLAY=:0 python3 leer_qr_raspberry.py\n"
            "Si lo vas a correr como servicio con systemd (ver "
            "README_RASPBERRY.md, sección 11), esa variable ya está puesta "
            "en el archivo .service -- ahí no hace falta hacer nada más."
        )
        lector_usb.detener()
        return

    def continuar_sin_conexion():
        # El usuario tocó el botón: deja de insistir con la pantalla de
        # "sin red" por ahora (sigue funcionando igual, todo se guarda en
        # la cola local) -- vuelve a aparecer solo si la red cambia de
        # estado de nuevo más adelante (ver hilo_red()).
        ventana.sin_red = False
        ventana.mostrar(TITULO_IDLE, SUBTITULO_IDLE, comun.COLOR_MARCA)

    ventana = VentanaTerminal(root, PANTALLA_COMPLETA, continuar_sin_conexion)

    id_temporizador_banner = None

    def volver_a_idle():
        ventana.mostrar_idle()

    def revisar_cola():
        nonlocal id_temporizador_banner
        mostro_leido = _drenar_cola(cola_codigos, control_duplicados, ventana, cola_wifi)
        mostro_resultado = _drenar_resultados(cola_resultados, ventana)
        mostro_red = _drenar_estado_red(cola_estado_red, ventana)
        if mostro_leido or mostro_resultado or mostro_red:
            if id_temporizador_banner:
                root.after_cancel(id_temporizador_banner)
            id_temporizador_banner = root.after(
                int(comun.BANNER_DURACION * 1000), volver_a_idle
            )

        if comun.apagar_solicitado.is_set():
            ventana.mostrar(
                "APAGANDO EL EQUIPO...", "Orden recibida desde el panel", comun.COLOR_DENEGADO
            )
            root.after(1500, root.destroy)
            return  # no se reprograma más: la ventana ya se va a cerrar

        root.after(REVISAR_COLA_MS, revisar_cola)

    root.after(REVISAR_COLA_MS, revisar_cola)
    root.mainloop()

    lector_usb.detener()

    if comun.apagar_solicitado.is_set():
        comun.apagar_equipo()


if __name__ == "__main__":
    main()
