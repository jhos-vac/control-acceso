"""
Lee un lector de código QR/barras USB tipo "keyboard wedge" -- como el
WD-1012 -- directamente del dispositivo de entrada de Linux (`evdev`), en
vez de depender de que una ventana tenga el foco del teclado.

Por qué así y no capturando teclas de la ventana: un lector de este tipo
se comporta exactamente como si alguien tipeara muy rápido el contenido
del QR y apretara Enter. Si se lo capturara desde la ventana de OpenCV
(como se hace con "R"/"ESC" en el terminal de PC), dejaría de funcionar
en cuanto la ventana pierda el foco -- algo que en un kiosco puede pasar
fácilmente (un clic afuera, el protector de pantalla, etc.). Leyendo el
dispositivo de entrada directamente, funciona sin importar qué tenga el
foco en ese momento.

Requiere:
- El paquete `evdev` (`pip install evdev`, o `sudo apt install
  python3-evdev`). Si no está instalado, este módulo igual se puede
  importar (para no romper el resto del programa) pero el lector USB
  simplemente no va a funcionar -- se avisa por consola.
- Permiso para leer `/dev/input/eventX`: agregar el usuario al grupo
  "input" (`sudo usermod -aG input $USER`, cerrar sesión y volver a
  entrar) o una regla udev. Ver README_RASPBERRY.md.
- Saber la ruta exacta del dispositivo (algo como
  `/dev/input/by-id/usb-..._WD-1012-event-kbd`) -- se obtiene con
  `ls /dev/input/by-id/` con el lector conectado. Ver README_RASPBERRY.md.

Asume distribución de teclado US QWERTY (lo habitual en estos lectores,
sin importar el idioma configurado en el sistema operativo, porque el
lector no usa la distribución del SO: manda directamente los códigos de
tecla de un teclado US). Si el contenido leído sale con caracteres raros,
lo más probable es que el lector esté configurado (por su propio menú de
códigos de barras de configuración, ver manual del WD-1012) en otra
distribución -- hay que configurarlo en el lector, no acá.
"""
import string
import threading
from typing import Callable, Optional

try:
    from evdev import InputDevice, categorize, ecodes
except ImportError:  # el módulo se puede importar igual sin evdev instalado
    InputDevice = None
    categorize = None
    ecodes = None


def _construir_mapa_teclas():
    """(código evdev) -> (carácter sin Shift, carácter con Shift).
    Cubre letras, dígitos y la puntuación que puede aparecer en la URL
    del QR (p.ej. https://its.academicok.com/datoscredencial?idperfil=X):
    letras, dígitos, ':', '/', '.', '?', '='."""
    if ecodes is None:
        return {}

    mapa = {}
    for letra in string.ascii_lowercase:
        codigo = getattr(ecodes, f"KEY_{letra.upper()}", None)
        if codigo is not None:
            mapa[codigo] = (letra, letra.upper())

    simbolos = {
        "KEY_1": ("1", "!"), "KEY_2": ("2", "@"), "KEY_3": ("3", "#"),
        "KEY_4": ("4", "$"), "KEY_5": ("5", "%"), "KEY_6": ("6", "^"),
        "KEY_7": ("7", "&"), "KEY_8": ("8", "*"), "KEY_9": ("9", "("),
        "KEY_0": ("0", ")"),
        "KEY_MINUS": ("-", "_"), "KEY_EQUAL": ("=", "+"),
        "KEY_SEMICOLON": (";", ":"), "KEY_APOSTROPHE": ("'", '"'),
        "KEY_SLASH": ("/", "?"), "KEY_DOT": (".", ">"), "KEY_COMMA": (",", "<"),
        "KEY_GRAVE": ("`", "~"), "KEY_SPACE": (" ", " "),
        "KEY_BACKSLASH": ("\\", "|"),
        "KEY_LEFTBRACE": ("[", "{"), "KEY_RIGHTBRACE": ("]", "}"),
    }
    for nombre, par in simbolos.items():
        codigo = getattr(ecodes, nombre, None)
        if codigo is not None:
            mapa[codigo] = par

    return mapa


MAPA_TECLAS = _construir_mapa_teclas()


class LectorTecladoUSB:
    """Escucha en segundo plano un dispositivo de entrada Linux y arma el
    texto tecla a tecla hasta que llega un Enter, momento en el que llama
    a `al_completar_codigo(texto)`."""

    def __init__(self, ruta_dispositivo: str, al_completar_codigo: Callable[[str], None]):
        self.ruta_dispositivo = ruta_dispositivo
        self.al_completar_codigo = al_completar_codigo
        self._detener = threading.Event()
        self._hilo: Optional[threading.Thread] = None

    def iniciar(self):
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()

    def detener(self):
        self._detener.set()

    def _bucle(self):
        if InputDevice is None:
            print(
                "[escaner] La librería 'evdev' no está instalada -- el lector QR "
                "USB no va a funcionar. Instálala con: pip install evdev"
            )
            return

        try:
            dispositivo = InputDevice(self.ruta_dispositivo)
        except Exception as error:
            print(
                f"[escaner] No se pudo abrir '{self.ruta_dispositivo}': {error}. "
                "Revisa SCANNER_DEVICE_PATH en .env y los permisos del grupo "
                "'input' (ver README_RASPBERRY.md)."
            )
            return

        print(f"[escaner] Escuchando el lector QR USB en {self.ruta_dispositivo}")
        buffer = []
        shift_activo = False

        try:
            for evento in dispositivo.read_loop():
                if self._detener.is_set():
                    break
                if evento.type != ecodes.EV_KEY:
                    continue

                tecla = categorize(evento)
                codigo = tecla.scancode
                valor = tecla.keystate  # 0=soltar, 1=apretar, 2=repetición

                if codigo in (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT):
                    shift_activo = valor != 0
                    continue

                if valor != 1:  # solo procesar el instante de apretar
                    continue

                if codigo in (ecodes.KEY_ENTER, ecodes.KEY_KPENTER):
                    if buffer:
                        codigo_leido = "".join(buffer)
                        buffer = []
                        self.al_completar_codigo(codigo_leido)
                    continue

                par = MAPA_TECLAS.get(codigo)
                if par:
                    buffer.append(par[1] if shift_activo else par[0])
        except Exception as error:
            print(f"[escaner] Se perdió la conexión con el lector USB: {error}")
