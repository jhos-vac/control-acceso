# Terminal en Raspberry Pi — guía de instalación

Esta es la guía para el terminal de **producción**: Raspberry Pi 4 +
pantalla táctil HDMI 5" + cámara del módulo Raspberry + lector QR USB de
mesa (WD-1012), los dos leyendo QR a la vez, montados en la carcasa
impresa (ver `../carcasa/`). El terminal de PC (`leer_qr.py`) sigue
sirviendo para probar sin tener la Raspberry a mano — la lógica que habla
con el backend es la misma para los dos (`comun.py`).

## 0. Qué necesitas antes de empezar

- Raspberry Pi 4
- Pantalla táctil HDMI 5" (800x480)
- Cámara del módulo Raspberry (cable plano a la ranura CSI)
- Lector QR USB de mesa WD-1012
- Una microSD — cualquiera de 16GB en adelante alcanza (Raspberry Pi OS
  usa unos 4-8GB; una de 64GB, que suele mostrar "59GB" disponibles por
  cómo se cuentan los GB, sobra de lejos)
- Un lector de tarjetas SD en tu PC, para grabarla
- Cable de red (recomendado por sobre WiFi — más estable para el latido
  hacia el backend)

## 1. Qué sistema operativo usar

**Raspberry Pi OS (64-bit), versión "with desktop"** — no la "Lite".

¿Por qué no Lite? Lite es más liviana porque no trae entorno de
escritorio, pero este terminal necesita mostrar una ventana (el banner de
colores con el resultado) en la pantalla táctil — con Lite hay que armar
esa parte a mano (compositor gráfico mínimo, etc.), que es más trabajo
para poco beneficio en un solo dispositivo por edificio. La versión
"with desktop" trae todo lo necesario (servidor gráfico, controlador de
la pantalla táctil, `picamera2` ya instalado en muchas imágenes) y se
configura para que arranque directo en el programa sin mostrar el
escritorio (modo kiosco, más abajo).

## 2. Grabar la SD

1. Instala [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
   en tu PC.
2. Elige el modelo **Raspberry Pi 4**, sistema operativo **Raspberry Pi
   OS (64-bit)** (la que dice "with desktop", no "Lite"), y tu tarjeta SD.
3. Antes de grabar, haz clic en el ícono de engranaje (⚙, "Editar
   opciones del sistema operativo" / `Ctrl+Shift+X`) y configura:
   - **Nombre de host**: por ejemplo `terminal-entrada-principal`.
   - **Usuario y contraseña**: elige un nombre de usuario (anota el que
     elijas — ya no es "pi" por defecto, y lo vas a necesitar más
     adelante para el servicio de arranque automático y los permisos).
   - **WiFi** (si no vas a usar cable): red y contraseña.
   - **Configuración regional**: zona horaria `America/Guayaquil`,
     teclado `es` (Latinoamérica/España, el que uses).
   - **Habilitar SSH**: actívalo (con contraseña) — te va a servir para
     configurar el resto sin tener que conectar un teclado a la Pi.
4. Graba y espera a que termine.

## 3. Primer arranque

1. Conecta la pantalla, la cámara (cable CSI, con la Pi **apagada**), el
   lector QR USB, el cable de red, y por último la alimentación.
2. Espera a que arranque (con SSH habilitado, también puedes conectarte
   desde tu PC: `ssh <usuario>@terminal-entrada-principal.local`, o con
   la IP que le haya asignado el router).
3. Actualiza el sistema:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

## 4. Probar la cámara

```bash
rpicam-hello --list-cameras
```

(En versiones más viejas del sistema el comando se llama
`libcamera-hello` en vez de `rpicam-hello` — si el primero no existe,
prueba con ese.) Debería listar tu cámara. Para ver la imagen en vivo
unos segundos y confirmar que enfoca:

```bash
rpicam-hello -t 5000
```

Si no aparece ninguna cámara: revisa que el cable CSI esté bien
insertado (con los contactos metálicos mirando hacia el conector HDMI) y
que quedó firme en ambos extremos (Pi y módulo de cámara).

## 5. Instalar dependencias

`opencv` y `picamera2` se instalan con `apt` (son los que trae Raspberry
Pi OS ya optimizados para el hardware de la Pi — instalarlos con `pip`
suele ser lento o directamente falla al compilar en una Raspberry):

```bash
sudo apt install -y python3-opencv python3-picamera2 python3-pip python3-venv git
```

Copia el proyecto a la Raspberry (o clónalo si ya está en tu GitHub —
ver `Backend_Base_de_Datos_Estado.md` del proyecto sobre el repo
`VAL-BACKEND`) en, por ejemplo, `/home/<usuario>/control-acceso/`.

Crea el entorno virtual **con acceso a los paquetes del sistema**
(`--system-site-packages`) para que dentro del venv se puedan usar
`cv2` y `picamera2`, que instalaste con `apt` y no existen como paquete
de pip instalable en la Pi:

```bash
cd ~/control-acceso/terminal
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements-raspberry.txt
```

## 6. Encontrar la ruta del lector QR USB (WD-1012)

Con el lector ya conectado por USB:

```bash
ls -l /dev/input/by-id/
```

Busca una línea que termine en `-event-kbd` (el WD-1012 se presenta ante
Linux como un teclado, porque es un lector "keyboard wedge" — manda el
código QR como si alguien lo tipeara). Algo como:

```
usb-SEM_USB_Keyboard-event-kbd -> ../event4
```

Copia esa ruta completa (`/dev/input/by-id/usb-SEM_USB_Keyboard-event-kbd`)
para el `.env` (siguiente paso). Si conectas más de un teclado/lector a
la vez y no estás seguro cuál es, desconecta todo menos el lector y
vuelve a correr el comando, o prueba leyendo eventos con
`sudo apt install -y evtest && sudo evtest` (te deja elegir el
dispositivo de una lista y ver los eventos en vivo mientras escaneas algo).

### Permisos para leer el dispositivo

Por defecto, leer directamente `/dev/input/eventX` requiere permisos de
administrador. Para que el terminal pueda leerlo sin correr como root,
agrega tu usuario al grupo `input`:

```bash
sudo usermod -aG input $USER
```

**Cierra sesión y vuelve a entrar** (o reinicia) para que el cambio de
grupo tenga efecto — no alcanza con solo correr el comando.

## 7. Configurar

```bash
cp .env.raspberry.example .env
nano .env
```

Ajusta al menos `API_URL` (si el backend corre en otra máquina de la
red, pon su IP, no `127.0.0.1`) y `SCANNER_DEVICE_PATH` (la ruta que
encontraste en el paso 6).

## 8. Probar

Con el backend corriendo y accesible desde la Raspberry (probar antes
con `curl http://<IP-del-backend>:8000/` desde la Pi, debería devolver
`{"status":"ok",...}`):

```bash
python3 leer_qr_raspberry.py
```

Se abre la ventana con la imagen de la cámara. Prueba:

- Mostrar un QR frente a la cámara → debería leerlo y consultar el
  backend.
- Escanear el mismo QR (o cualquier código) con el lector de mesa →
  también debería leerlo y consultar el backend, sin que la ventana
  necesite tener el foco (ver el aviso `[escaner] Escuchando el lector
  QR USB en ...` en la consola al arrancar).
- Los dos a la vez deberían funcionar sin pisarse: si detectan el mismo
  QR casi al mismo tiempo, solo se registra una vez (`TIEMPO_ANTIDUPLICADO`
  en `.env`).

Si algo no anda, revisa primero la consola — imprime avisos claros
(cámara no encontrada, lector no encontrado, backend no contesta, etc.).

## 9. Apagado remoto — permiso de sudo sin contraseña

El botón "Apagar" del panel ya funciona con Linux (`sudo shutdown -h now`),
pero necesita que el usuario que corre el script pueda apagar sin que se
le pida contraseña (si no, el comando queda esperando la contraseña para
siempre y nunca se apaga). Configúralo así:

```bash
sudo visudo -f /etc/sudoers.d/control-acceso
```

Y agrega esta línea (reemplaza `<usuario>` por el que elegiste al grabar
la SD):

```
<usuario> ALL=(ALL) NOPASSWD: /sbin/shutdown
```

Guarda y cierra. Prueba desde el panel (botón "Apagar" en Puntos de
acceso) — la Raspberry debería apagarse sola en los próximos segundos.

## 10. Encendido remoto — limitación importante

El panel también tiene un botón "Encender" (Wake-on-LAN, ver
`Backend_Base_de_Datos_Estado.md` del proyecto). **Con una Raspberry Pi
completamente apagada, en general esto NO va a funcionar**: a diferencia
de una PC de escritorio, la Raspberry Pi no mantiene su interfaz de red
con energía en espera cuando está apagada — no hay quien reciba el
paquete de encendido. Si necesitas de verdad poder encenderla a
distancia, la alternativa realista es un enchufe/relé inteligente (WiFi,
tipo Sonoff/Tapo) que corte y reponga la energía física de la Raspberry
— eso sí funciona siempre, sin depender del soporte de la placa. No está
incluido en este proyecto todavía; es hardware adicional a decidir aparte.

## 11. Modo kiosco (arranque automático + pantalla completa)

### Arranque automático (systemd)

Para que el terminal arranque solo al encender la Raspberry, sin tener
que iniciar sesión y correrlo a mano:

1. Edita `control-acceso-terminal.service` (en esta misma carpeta) y
   reemplaza `<USUARIO>` por tu usuario real (las 4 apariciones).
2. Cópialo e instálalo:

```bash
sudo cp control-acceso-terminal.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable control-acceso-terminal.service
sudo systemctl start control-acceso-terminal.service
```

3. Revisa que arrancó bien:

```bash
sudo systemctl status control-acceso-terminal.service
journalctl -u control-acceso-terminal.service -f   # logs en vivo
```

Con esto, si la Raspberry se reinicia sola (por un corte de luz, por
ejemplo) o el programa se cae por algún error, vuelve a arrancar solo
(`Restart=on-failure` en el archivo de servicio).

### Pantalla completa

Pon `PANTALLA_COMPLETA=true` en `.env` para que la ventana ocupe toda la
pantalla táctil.

### Ocultar el escritorio y que no se apague la pantalla

Para que se vea como un kiosco de verdad (sin barra de tareas, sin que
la pantalla se apague sola):

- Desactivar el protector/apagado de pantalla: `sudo raspi-config` →
  *Display Options* → *Screen Blanking* → deshabilitar. (O, desde la
  interfaz gráfica: *Preferencias* → *Raspberry Pi Configuration* →
  pestaña *Display*.)
- Ocultar el mouse cuando no se mueve (opcional, prolijo si usan touch):
  `sudo apt install -y unclutter` y agregarlo también al autoarranque.
- Si además quieres ocultar la barra de tareas del escritorio, se puede,
  pero ya es un ajuste más fino del entorno gráfico (LXDE/Wayfire según
  la versión) — te lo detallo si llegas a necesitarlo, no es
  imprescindible para que el sistema funcione.

## 12. Problemas comunes

- **La ventana no abre / error de `picamera2`**: confirma que instalaste
  con `apt` (paso 5) y que creaste el venv con `--system-site-packages`
  — si el venv no tiene esa opción, no va a "ver" `picamera2` ni `cv2`
  aunque estén instalados en el sistema.
- **El lector USB no lee nada**: revisa que cerraste sesión después del
  `usermod -aG input` (paso 6), que `SCANNER_DEVICE_PATH` en `.env` es
  exactamente la ruta que viste en `/dev/input/by-id/`, y que el aviso
  `[escaner] Escuchando...` aparece en la consola al arrancar (si dice
  que no pudo abrir el dispositivo, es casi siempre permisos o ruta mal
  copiada).
- **Caracteres raros al leer con el lector USB** (por ejemplo aparece
  `Zttps` en vez de `https`): el lector está configurado en otra
  distribución de teclado que no es US — hay que cambiarlo desde los
  códigos de configuración del propio WD-1012 (ver su manual), no desde
  el sistema operativo.
- **"Network Error" o no contacta al backend**: prueba
  `curl http://<IP-del-backend>:8000/` desde la Raspberry; si no
  contesta, es un tema de red (firewall, IP incorrecta en `.env`, o el
  backend no está corriendo), no del terminal.
- **No se apaga con el botón del panel**: revisa el paso 9 (sudoers) —
  es la causa más común.

## Ver también

- [[Backend_Base_de_Datos_Estado]] — endpoints de latido/apagado/encendido.
- [[Carcasa_3D_Terminal_Estado]] — carcasa donde va montado todo esto.
- `../backend/README.md` — cómo levantar el backend.
