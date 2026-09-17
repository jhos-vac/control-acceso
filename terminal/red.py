"""
Manejo de red (WiFi) para el terminal de Raspberry Pi -- pensado para que
el dispositivo sea autónomo: si no encuentra la red que tenía configurada,
el usuario puede escanear un código QR de WiFi (el mismo tipo que genera
cualquier router o que se comparte desde un celular -- formato estándar
"WIFI:T:...;S:...;P:...;;") con el MISMO lector USB que ya usa para las
credenciales, sin hardware extra.

Usa `nmcli` (NetworkManager), que viene instalado y activo por defecto en
Raspberry Pi OS (Bookworm en adelante, la versión que recomienda
README_RASPBERRY.md). No hace falta ninguna librería de Python adicional
-- son llamadas a `nmcli` por `subprocess`, igual que `comun.apagar_equipo()`
llama a `shutdown`.

Requiere el permiso de sudo sin contraseña para `nmcli` (ver
README_RASPBERRY.md, sección de sudoers) -- sin eso, `conectar_wifi()`
se queda esperando una contraseña que nunca llega y falla por timeout.
"""
import re
import subprocess

TIMEOUT_CONSULTA = 5      # segundos para preguntar el estado de red
TIMEOUT_CONEXION = 25     # segundos para esperar a que nmcli conecte


def es_codigo_wifi(codigo):
    """True si el texto leído tiene pinta de ser un código QR de WiFi
    (formato estándar "WIFI:...;;") y no un QR de credencial normal."""
    return codigo.strip().upper().startswith("WIFI:")


def _valor_campo(contenido, letra):
    """Extrae el valor de un campo (T/S/P/H) de un código WIFI:...;;,
    respetando que los caracteres ; , : y \\ puedan venir "escapados" con
    una barra invertida adelante dentro del valor -- así lo genera
    cualquier app/router que siga el formato estándar."""
    patron = rf"(?<!\\){letra}:((?:\\.|[^;])*)"
    coincidencia = re.search(patron, contenido)
    if not coincidencia:
        return None
    valor = coincidencia.group(1)
    for escapado, real in (("\\;", ";"), ("\\,", ","), ("\\:", ":"), ("\\\\", "\\")):
        valor = valor.replace(escapado, real)
    return valor


def parsear_codigo_wifi(codigo):
    """Devuelve {"ssid", "password", "tipo", "oculta"} a partir de un
    código "WIFI:T:WPA;S:MiRed;P:MiClave;;", o None si no tiene el
    formato esperado (por ejemplo, si no trae SSID)."""
    if not es_codigo_wifi(codigo):
        return None
    ssid = _valor_campo(codigo, "S")
    if not ssid:
        return None
    return {
        "ssid": ssid,
        "password": _valor_campo(codigo, "P") or "",
        "tipo": (_valor_campo(codigo, "T") or "WPA").upper(),
        "oculta": (_valor_campo(codigo, "H") or "false").lower() == "true",
    }


def hay_red():
    """True si NetworkManager reporta alguna conexión activa (WiFi o
    cable) -- NO confirma que el backend en sí sea alcanzable, solo que
    el dispositivo tiene una red. Que el backend no conteste con la red
    presente ya lo maneja `comun.hilo_envio()` (cola local, reintentos)
    sin necesidad de esta pantalla."""
    try:
        resultado = subprocess.run(
            ["nmcli", "-t", "-f", "STATE", "general"],
            capture_output=True, text=True, timeout=TIMEOUT_CONSULTA,
        )
        return resultado.returncode == 0 and resultado.stdout.strip() == "connected"
    except Exception:
        return False


def conectar_wifi(ssid, password, tipo="WPA"):
    """Intenta conectar a una red WiFi con nmcli (requiere sudo sin
    contraseña, ver README_RASPBERRY.md). Devuelve (ok: bool, mensaje: str)."""
    try:
        if tipo == "NOPASS" or not password:
            comando = ["sudo", "nmcli", "device", "wifi", "connect", ssid]
        else:
            comando = ["sudo", "nmcli", "device", "wifi", "connect", ssid, "password", password]
        resultado = subprocess.run(
            comando, capture_output=True, text=True, timeout=TIMEOUT_CONEXION
        )
        if resultado.returncode == 0:
            return True, f"Conectado a {ssid}."
        detalle = (resultado.stderr or resultado.stdout or "nmcli no pudo conectar").strip()
        return False, detalle
    except subprocess.TimeoutExpired:
        return False, "Se agotó el tiempo esperando la conexión."
    except Exception as error:
        return False, str(error)
