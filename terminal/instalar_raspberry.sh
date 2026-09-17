#!/usr/bin/env bash
# Instalación con un solo script del terminal de Raspberry Pi.
#
# Hace todo lo que describe README_RASPBERRY.md paso a paso (secciones
# 5, 6, 7, 9 y 11) de una sola vez, para que el dispositivo quede
# funcionando solo desde el próximo arranque -- "que baste con
# encenderlo". Pensado para correrse UNA vez, recién copiado el
# proyecto a la Raspberry (ver README_RASPBERRY.md, sección 4).
#
# Uso:
#   cd ~/control-acceso/terminal
#   chmod +x instalar_raspberry.sh
#   ./instalar_raspberry.sh
#
# No hace falta sudo para correrlo (el script pide sudo el mismo, línea
# por línea, donde hace falta) -- así queda claro qué partes tocan el
# sistema y cuáles no.
#
# Es seguro volver a correrlo si algo falla a mitad de camino: cada paso
# revisa si ya está hecho antes de repetirlo.

set -euo pipefail

CARPETA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$CARPETA"

echo "========================================================"
echo " Instalación del terminal de Raspberry Pi (control-acceso)"
echo " Carpeta: $CARPETA"
echo "========================================================"
echo

if [ ! -f "leer_qr_raspberry.py" ]; then
    echo "ERROR: este script debe correrse desde la carpeta 'terminal'"
    echo "del proyecto (no se encontró leer_qr_raspberry.py acá)."
    exit 1
fi

USUARIO="$(whoami)"
echo "Usuario detectado: $USUARIO"
echo

# ------------------------------------------------------------------
# 1. Paquetes de sistema (README_RASPBERRY.md, sección 5)
# ------------------------------------------------------------------
echo "--- 1/7: Paquetes de sistema (apt) ---"
sudo apt update
sudo apt install -y python3-pip python3-venv python3-tk git
echo "OK"
echo

# ------------------------------------------------------------------
# 2. Grupo 'input' para leer el lector USB sin ser root (sección 6)
# ------------------------------------------------------------------
echo "--- 2/7: Permiso para leer el lector QR USB ---"
if id -nG "$USUARIO" | grep -qw input; then
    echo "El usuario '$USUARIO' ya está en el grupo 'input'."
else
    sudo usermod -aG input "$USUARIO"
    echo "Usuario agregado al grupo 'input'."
    echo "IMPORTANTE: este cambio necesita cerrar sesión y volver a entrar"
    echo "(o reiniciar) para tener efecto -- el script sigue igual, pero"
    echo "acordate de reiniciar al final."
fi
echo

# ------------------------------------------------------------------
# 3. Entorno virtual + dependencias de Python (sección 5)
# ------------------------------------------------------------------
echo "--- 3/7: Entorno virtual de Python ---"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements-raspberry.txt
deactivate
echo "OK"
echo

# ------------------------------------------------------------------
# 4. Archivo .env (sección 7)
# ------------------------------------------------------------------
echo "--- 4/7: Archivo de configuración (.env) ---"
if [ -f ".env" ]; then
    echo "Ya existe un .env -- no se toca (podés editarlo a mano con"
    echo "'nano .env' si hace falta cambiar algo)."
else
    cp .env.raspberry.example .env
    echo "Se creó .env a partir de .env.raspberry.example."
    echo "TODAVÍA HACE FALTA que edites a mano, como mínimo:"
    echo "  - API_URL             (la IP del backend en tu red)"
    echo "  - SCANNER_DEVICE_PATH (ver README_RASPBERRY.md, sección 6,"
    echo "                         'Encontrar la ruta del lector QR USB')"
    echo "Corré 'nano .env' cuando termine este script."
fi
echo

# ------------------------------------------------------------------
# 5. Permisos de sudo sin contraseña: apagado + WiFi (sección 9)
# ------------------------------------------------------------------
echo "--- 5/7: Permisos de sudo sin contraseña (apagado + WiFi) ---"
RUTA_NMCLI="$(command -v nmcli || echo /usr/bin/nmcli)"
ARCHIVO_SUDOERS="/etc/sudoers.d/control-acceso"
CONTENIDO_SUDOERS="$USUARIO ALL=(ALL) NOPASSWD: /sbin/shutdown
$USUARIO ALL=(ALL) NOPASSWD: $RUTA_NMCLI"

if [ -f "$ARCHIVO_SUDOERS" ] && sudo grep -qF "$RUTA_NMCLI" "$ARCHIVO_SUDOERS" \
   && sudo grep -qF "/sbin/shutdown" "$ARCHIVO_SUDOERS"; then
    echo "Los permisos de sudo ya estaban configurados."
else
    TEMPORAL="$(mktemp)"
    echo "$CONTENIDO_SUDOERS" > "$TEMPORAL"
    if sudo visudo -c -f "$TEMPORAL" >/dev/null 2>&1; then
        sudo install -m 0440 "$TEMPORAL" "$ARCHIVO_SUDOERS"
        echo "Permisos de sudo configurados en $ARCHIVO_SUDOERS."
    else
        echo "ERROR: el archivo de sudoers generado no es válido, no se instaló."
        echo "Revisá manualmente con: sudo visudo -f $ARCHIVO_SUDOERS"
    fi
    rm -f "$TEMPORAL"
fi
echo

# ------------------------------------------------------------------
# 6. Arranque automático: systemd + autologin al escritorio (sección 11)
# ------------------------------------------------------------------
echo "--- 6/7: Arranque automático (systemd + autologin de escritorio) ---"

# El servicio systemd corre con DISPLAY=:0, es decir, asume que ya hay
# una sesión de escritorio abierta en la pantalla -- por eso hace falta
# que la Raspberry inicie sesión sola, sin pedir usuario/contraseña.
if command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_boot_behaviour B4
    echo "Autologin de escritorio activado (raspi-config B4)."
else
    echo "AVISO: no se encontró raspi-config -- activá el autologin de"
    echo "escritorio a mano (Raspberry Pi OS: raspi-config > System"
    echo "Options > Boot / Auto Login > Desktop Autologin)."
fi

SERVICIO="control-acceso-terminal.service"
if [ -f "$SERVICIO" ]; then
    # Reemplaza <USUARIO> (usuario) y además fija WorkingDirectory/ExecStart
    # a la carpeta REAL donde está este script -- así funciona sin
    # importar si el proyecto quedó en ~/control-acceso/terminal o en
    # cualquier otra carpeta (por ejemplo, la carpeta "solo lo necesario
    # para la Raspberry" con otro nombre).
    sed \
        -e "s/<USUARIO>/$USUARIO/g" \
        -e "s#WorkingDirectory=.*#WorkingDirectory=$CARPETA#" \
        -e "s#ExecStart=.*#ExecStart=$CARPETA/.venv/bin/python3 $CARPETA/leer_qr_raspberry.py#" \
        "$SERVICIO" | sudo tee "/etc/systemd/system/$SERVICIO" >/dev/null
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICIO"
    echo "Servicio '$SERVICIO' instalado y habilitado para arrancar solo."
    echo "(Todavía no se inició ahora mismo -- ver el aviso final.)"
else
    echo "ERROR: no se encontró $SERVICIO en esta carpeta."
fi
echo

# ------------------------------------------------------------------
# 7. Resumen
# ------------------------------------------------------------------
echo "--- 7/7: Listo ---"
echo "========================================================"
echo " Instalación completa."
echo "========================================================"
echo
echo "Antes de reiniciar, confirmá que .env está bien configurado"
echo "(API_URL y SCANNER_DEVICE_PATH, sobre todo):"
echo "  nano .env"
echo
echo "Después, reiniciá la Raspberry -- el terminal debería arrancar"
echo "solo, en pantalla completa, sin necesitar teclado ni iniciar"
echo "sesión a mano:"
echo "  sudo reboot"
echo
echo "Para revisar que arrancó bien tras el reinicio:"
echo "  sudo systemctl status control-acceso-terminal.service"
echo "  journalctl -u control-acceso-terminal.service -f"
