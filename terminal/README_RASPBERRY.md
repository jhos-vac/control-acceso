# Terminal en Raspberry Pi — guía de instalación

Esta es la guía para el terminal de **producción**: Raspberry Pi 4 +
pantalla táctil HDMI 5" + lector QR USB de mesa (WD-1012), montados en
la carcasa impresa (ver `../carcasa/`). El terminal **solo lee QR con el
lector USB de mesa** — no usa cámara. El terminal de PC (`leer_qr.py`)
sigue sirviendo para probar sin tener la Raspberry a mano — la lógica
que habla con el backend es la misma para los dos (`comun.py`).

> Si en algún momento hace falta agregar lectura por cámara de nuevo,
> `leer_qr_raspberry.py` tiene una nota al principio explicando cómo
> reincorporarla sin tocar el resto del programa.

## 0. Qué necesitas antes de empezar

- Raspberry Pi 4
- Pantalla táctil HDMI 5" (800x480)
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
la pantalla táctil, Python con Tkinter) y se configura para que arranque
directo en el programa sin mostrar el escritorio (modo kiosco, más
abajo).

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

1. Conecta la pantalla, el lector QR USB, el cable de red, y por último
   la alimentación.
2. Espera a que arranque (con SSH habilitado, también puedes conectarte
   desde tu PC: `ssh <usuario>@terminal-entrada-principal.local`, o con
   la IP que le haya asignado el router).
3. Actualiza el sistema:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

## 4. Descargar el proyecto (GitHub o copia directa por SSH)

Para descargar con `git clone` (4.2) necesitas estar conectado a la
Raspberry por SSH (ya la abriste en el paso 3, así que si dejaste esa
terminal abierta puedes saltar directo a "4.2 Descargar con
`git clone`" más abajo). Si prefieres copiar los archivos directo desde
tu PC sin usar un repositorio, ve a "4.3 Alternativa sin GitHub: copiar
el archivo/carpeta directo por SSH (`scp`)".

### 4.1 Conectarte por SSH

Necesitas: la Raspberry encendida y en la misma red (cable o WiFi) que tu
PC, y SSH habilitado (lo activaste al grabar la SD, paso 2). Desde una
terminal de tu PC:

1. **Windows**: abre **PowerShell** (no hace falta instalar nada aparte,
   `ssh` viene incluido desde Windows 10). En **Mac/Linux**: abre la
   Terminal.
2. Intenta conectarte por el nombre de host que le pusiste al grabar la
   SD, agregando `.local` al final:

   ```bash
   ssh <usuario>@<nombre-de-host>.local
   ```

   Por ejemplo, si el usuario es `jhos` y el host es
   `terminal-entrada-principal-huaynacapac`:

   ```bash
   ssh jhos@terminal-entrada-principal-huaynacapac.local
   ```

3. **La primera vez** que te conectas a una Raspberry nueva, vas a ver
   un mensaje parecido a este:

   ```
   The authenticity of host '...' can't be established.
   ED25519 key fingerprint is SHA256:...
   Are you sure you want to continue connecting (yes/no/[fingerprint])?
   ```

   Esto es normal (tu PC nunca "vio" esta Raspberry antes) — escribe
   `yes` y presiona Enter. Esa pregunta no vuelve a aparecer en
   conexiones futuras desde la misma PC.
4. Te va a pedir la contraseña del usuario (la que elegiste al grabar la
   SD, paso 2). Escríbela y presiona Enter — **no vas a ver los
   caracteres ni asteriscos mientras escribes**, es normal en SSH,
   sigue escribiendo y da Enter igual.
5. Si todo salió bien, el prompt de tu terminal cambia a algo como
   `jhos@terminal-entrada-principal-huaynacapac:~ $` — eso confirma que
   ya estás **dentro de la Raspberry**, no en tu PC. De aquí en adelante,
   todos los comandos de esta guía (incluidos los del resto de esta
   sección y las siguientes) se escriben en esa misma ventana.

**Si `ssh <usuario>@<nombre-de-host>.local` no conecta** (a veces
`.local` no resuelve, sobre todo en redes WiFi de algunas instituciones):

- Busca la IP que le asignó el router a la Raspberry. La forma más
  simple es entrar a la página de administración del router (revisa la
  lista de dispositivos conectados, busca uno con el nombre de host que
  le pusiste) o, si tienes un teclado/mouse conectados directo a la
  Raspberry, correr `hostname -I` ahí mismo.
- Conéctate usando esa IP en vez del nombre:

  ```bash
  ssh <usuario>@192.168.1.XX
  ```

- Si la conexión se rechaza por completo (no solo "no encuentra el
  host"), confirma que habilitaste SSH al grabar la SD (paso 2) y que la
  Raspberry ya terminó de arrancar.

Para salir de la sesión SSH en cualquier momento (sin apagar la
Raspberry): escribe `exit` y Enter.

### 4.2 Descargar con `git clone`

El repositorio del proyecto es `https://github.com/jhos-vac/control-acceso`.
**Ya conectado por SSH a la Raspberry** (sección 4.1):

```bash
sudo apt install -y git
cd ~
git clone https://github.com/jhos-vac/control-acceso.git control-acceso
```

(Si el repositorio es privado, `git clone` por HTTPS va a pedir usuario y
contraseña y va a fallar en una Raspberry sin teclado: usa una *deploy
key* de solo lectura, ver `../DESPLIEGUE.md`, paso 3, o la alternativa
4.3 de abajo.)

Esto descarga todo el proyecto (`backend/`, `frontend/`, `terminal/`,
etc.) a `/home/<usuario>/control-acceso/`. Los pasos siguientes de esta
guía asumen esa ruta.

Para traer cambios más adelante (por ejemplo, después de que actualices
`leer_qr_raspberry.py` en tu PC y los subas al repositorio):

```bash
cd ~/control-acceso
git pull
```

### 4.3 Alternativa sin GitHub: copiar el archivo/carpeta directo por SSH (`scp`)

Si por ahora no quieres usar un repositorio, puedes copiar los archivos
de tu Escritorio directo a la Raspberry con `scp` (viene incluido junto
con `ssh` en Windows 10/11, Mac y Linux — no hay que instalar nada
aparte). Es más manual que `git clone`/`git pull` — cualquier cambio
futuro hay que volver a copiarlo a mano — pero funciona igual para
levantar el terminal, y es la opción más simple mientras no tengas
listo el repositorio correcto.

**Importante:** `scp` se corre **desde tu PC**, no desde la sesión SSH
que abriste en el paso 4.1 (ahí estás *dentro* de la Raspberry, y ahí no
están tus archivos). Si dejaste esa ventana abierta, abre una **ventana
nueva** de PowerShell/Terminal para lo que sigue (o escribe `exit` en la
que ya tienes, para volver a tu PC, y reusa esa misma).

**Copiar una sola carpeta** (por ejemplo, toda tu carpeta `control-acceso`
del Escritorio) — el `-r` es necesario para copiar carpetas completas,
no solo archivos sueltos:

```powershell
scp -r "C:\Users\Jhostin\Desktop\control-acceso" jhos@terminal-entrada-principal-huaynacapac.local:~/
```

Esto la deja en `/home/jhos/control-acceso/` en la Raspberry (reemplaza
`jhos` y el nombre de host por los tuyos si son distintos). Te va a
pedir la contraseña del usuario de la Raspberry, igual que al conectarte
por SSH.

**Copiar un solo archivo** (por ejemplo, si solo cambiaste
`leer_qr_raspberry.py` y ya tienes el resto en la Raspberry):

```powershell
scp "C:\Users\Jhostin\Desktop\control-acceso\terminal\leer_qr_raspberry.py" jhos@terminal-entrada-principal-huaynacapac.local:~/control-acceso/terminal/
```

Esto sobrescribe ese archivo puntual en la Raspberry con el de tu PC —
útil para ir probando cambios sin volver a copiar todo.

Si `.local` no te conectó en el paso 4.1, usa la misma IP que
encontraste ahí en vez del nombre de host (`scp -r "..." jhos@192.168.1.XX:~/`).

Si prefieres no usar la red para esto (por ejemplo, la Raspberry todavía
no tiene salida a tu WiFi), la alternativa es copiar la carpeta a un
pendrive y pasarla así — pero como ya tienes SSH funcionando desde el
paso 3, normalmente `scp` es más rápido.

## 5. Instalar dependencias

```bash
sudo apt install -y python3-pip python3-venv python3-tk git
```

`python3-tk` es el único paquete de sistema que hace falta (le da a
Python el soporte de Tkinter, la ventana del terminal) — ya no se
necesitan `python3-opencv` ni `python3-picamera2`, porque este terminal
no usa cámara.

Crea el entorno virtual (ya no hace falta `--system-site-packages`,
porque no depende de ningún paquete instalado por `apt` como antes con
`cv2`/`picamera2` — todo lo que usa este terminal se instala con pip):

```bash
cd ~/control-acceso/terminal
python3 -m venv .venv
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
red, pon su IP, no `127.0.0.1`; con el backend en la nube, su URL
pública HTTPS), `SCANNER_DEVICE_PATH` (la ruta que encontraste en el
paso 6) y, si el backend tiene `TERMINAL_API_KEY` configurada (siempre
en producción), `API_KEY` con **el mismo valor**. Sin `SCANNER_DEVICE_PATH`
el terminal no tiene forma de leer ningún QR — no hay cámara de respaldo.
Con una `API_KEY` incorrecta el backend contesta `401`: no se pierde nada
(los QR quedan en la cola local y se envían cuando se corrige), pero no
se registra hasta entonces.

## 8. Probar

Con el backend corriendo y accesible desde la Raspberry (probar antes
con `curl http://<IP-del-backend>:8000/` desde la Pi, debería devolver
`{"status":"ok",...}`):

```bash
python3 leer_qr_raspberry.py
```

> **Si estás probando por SSH** (conectado desde tu PC, como en el paso
> 4.1) en vez de sentado frente a la pantalla de la Raspberry: la
> ventana necesita una sesión de escritorio activa, y por SSH no hay
> ninguna variable `DISPLAY` puesta por defecto. Si el escritorio de la
> Raspberry ya está abierto en su propia pantalla (lo normal, arranca
> así con Raspberry Pi OS "with desktop"), antepone la variable al
> comando:
>
> ```bash
> DISPLAY=:0 python3 leer_qr_raspberry.py
> ```
>
> Esto solo hace falta para probar manualmente por SSH — una vez
> configurado el arranque automático (paso 11), el archivo `.service` ya
> trae `DISPLAY=:0` y no hay que hacer nada especial.

Se abre la ventana del terminal (fondo de color + "CONTROL DE ACCESO" +
"Acerque su código QR al lector"). Prueba:

- Escanear un QR con el lector de mesa → el fondo cambia enseguida a
  color institucional con "Código leído, Registrando..." (esto es
  inmediato, no espera al backend — ver "Velocidad" más abajo), y un
  instante después se actualiza con el resultado real: verde ENTRADA,
  ámbar SALIDA, rojo DENEGADO, púrpura DUPLICADO (ver más abajo), o gris
  si no hay conexión. Vuelve solo a la pantalla de espera después de
  unos segundos.
- Todo esto sin que la ventana necesite tener el foco (ver el aviso
  `[escaner] Escuchando el lector QR USB en ...` en la consola al
  arrancar).
- Escanear el mismo QR dos veces seguidas muy rápido (en menos de
  `TIEMPO_ANTIDUPLICADO` segundos) → la segunda lectura se ignora del
  todo, ni siquiera se manda — pensado para filtrar una doble lectura
  del mismo código por el lector, no para la persona.

Si algo no anda, revisa primero la consola — imprime avisos claros
(lector no encontrado, `SCANNER_DEVICE_PATH` no configurado, backend no
contesta, etc.).

### Velocidad: por qué la lectura no espera a la red

Cada código leído se guarda de inmediato en un archivo local
(`cola_local.db`, en esta misma carpeta — no hace falta instalarlo,
`sqlite3` viene con Python) y el terminal sigue leyendo el siguiente sin
esperar nada; un hilo aparte, en segundo plano, va mandando esos
pendientes al backend uno por uno. Así, con mucha gente entrando
seguida, cada persona solo espera lo que tarda el lector en leer el
código (normalmente 1-2 segundos) — no lo que tarde la red o el backend
en responder. El resultado real (verde/ámbar/rojo/púrpura) se actualiza
en pantalla apenas llega la respuesta, que casi siempre es cuestión de
milisegundos si la red anda bien.

### Funciona sin conexión — nada se pierde

Si se corta la red o el backend deja de responder, los códigos leídos
**no se pierden**: quedan guardados en `cola_local.db` (en disco, así
que sobreviven un corte de luz o un reinicio del terminal) hasta que
vuelva la conexión. La consola avisa algo así mientras tanto:

```
[18:16:09] QR leído (lector USB), en cola para enviar (1 pendiente(s))
  -> Sin conexión (No se pudo contactar al backend: ...). 1 pendiente(s) por enviar, reintentando...
```

En cuanto vuelve la red, se mandan todos solos, en el mismo orden en que
se leyeron (importante: así el backend calcula bien ENTRADA/SALIDA de
cada persona según el momento REAL en que escaneó, no cuando se pudo
mandar). Si estuvo offline un buen rato y se está poniendo al día con
varios pendientes acumulados, la pantalla **no** se pone a mostrar cada
uno de esos resultados viejos (esas personas ya se fueron) — solo
resultados de lecturas recientes (`MOSTRAR_RESULTADO_SEGUNDOS` en `.env`,
20 segundos por defecto). Igual quedan todos bien registrados en el
backend, solo no se muestran en pantalla.

Para probarlo: para el backend (`Ctrl+C` en su ventana), escanea un par
de QR (la consola avisa que quedaron pendientes), y vuelve a levantar el
backend — deberían enviarse solos en los siguientes segundos.

### Marca duplicada (alguien no está seguro si ya marcó)

Si la misma persona escanea dos veces dentro de
`MINUTOS_ANTIDUPLICADO_MOVIMIENTO` (esto se configura en el **backend**,
`backend/.env` — no en el terminal, ver `backend/README.md`), la segunda
vez el fondo se pone **púrpura** con "⚠ MARCA DUPLICADA" y un mensaje
como "Ya se había registrado ENTRADA hace 2 min" — no se alterna a
SALIDA por error. No se crea ningún registro nuevo para esa segunda
lectura.

### WiFi de respaldo: qué pasa si el terminal se queda sin red

El terminal revisa solo, cada `REVISAR_RED_SEGUNDOS` (5 segundos por
defecto), si tiene alguna red activa. Si no la tiene, la pantalla de
espera cambia sola a fondo gris con **"SIN CONEXIÓN WIFI"** y ofrece dos
salidas, sin necesitar teclado ni mouse — pensado para que cualquiera
pueda resolverlo ahí mismo, sin llamar a nadie:

- **Escanear un código QR de WiFi** con el mismo lector de mesa que ya
  usan las credenciales — el terminal reconoce que no es un QR de
  credencial (no lo manda al backend) y en cambio intenta conectarse a
  esa red. La pantalla avisa "Conectando a WiFi..." y después "✓
  CONECTADO" (verde) o "✗ NO SE PUDO CONECTAR" con el motivo (rojo) —
  por ejemplo, si la clave está mal. Cualquier celular puede generar
  este tipo de código (en Android, desde los ajustes de WiFi → compartir
  red → código QR; en iPhone, mantén presionada la red en ajustes WiFi).
- **Tocar el botón "Continuar sin conexión"** en la pantalla (es
  táctil) — el terminal sigue funcionando exactamente igual, guardando
  todo en la cola local (ver "Funciona sin conexión" más arriba) hasta
  que vuelva a haber red. El aviso no vuelve a aparecer solo hasta que
  el estado de la red realmente cambie de nuevo.

Esto requiere el permiso de sudo sin contraseña para `nmcli` — ver el
siguiente paso.

## 9. Permisos de sudo sin contraseña (apagado remoto + WiFi de respaldo)

Dos cosas del terminal necesitan poder correr un comando con `sudo` **sin
que se pida contraseña** (si no, el comando se queda esperando una
contraseña que nunca llega, y en la práctica no funciona):

- El botón "Apagar" del panel (`sudo shutdown -h now`).
- Conectarse a una red WiFi nueva desde la pantalla "SIN CONEXIÓN WIFI"
  (`sudo nmcli ...`, ver el paso anterior).

Configura ambos permisos juntos:

```bash
sudo visudo -f /etc/sudoers.d/control-acceso
```

Y agrega estas dos líneas (reemplaza `<usuario>` por el que elegiste al
grabar la SD):

```
<usuario> ALL=(ALL) NOPASSWD: /sbin/shutdown
<usuario> ALL=(ALL) NOPASSWD: /usr/bin/nmcli
```

> Si `which nmcli` te da una ruta distinta a `/usr/bin/nmcli`, usa esa
> ruta en la línea de arriba (es lo normal en Raspberry Pi OS, pero
> puede variar según la versión).

Guarda y cierra. Prueba el apagado desde el panel (botón "Apagar" en
Puntos de acceso) — la Raspberry debería apagarse sola en los próximos
segundos. Para probar el WiFi de respaldo, ver el paso anterior.

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

- **`_tkinter.TclError: no display name and no $DISPLAY environment
  variable`**: estás corriendo el script por SSH y no hay ninguna
  sesión de escritorio con `DISPLAY` puesta en esa conexión — ver el
  recuadro del paso 8. Solución rápida:

  ```bash
  DISPLAY=:0 python3 leer_qr_raspberry.py
  ```

  Esto asume que el escritorio de la Raspberry ya está abierto en su
  propia pantalla (lo normal con Raspberry Pi OS "with desktop", que
  arranca con inicio de sesión automático). Si aun así falla, confirma
  que hay una sesión de escritorio activa con `loginctl list-sessions`
  (debería listar una sesión en `seat0` con tu usuario). Con el servicio
  systemd del paso 11 esto no pasa — el archivo `.service` ya trae
  `DISPLAY=:0`.
- **`[escaner] No se pudo abrir '/dev/input/by-id/...': [Errno 2] No
  such file or directory`**: el `SCANNER_DEVICE_PATH` de `.env` no
  coincide con ningún dispositivo conectado ahora mismo. Vuelve a
  correr `ls -l /dev/input/by-id/` (paso 6) con el lector ya enchufado
  y compara con lo que tienes en `.env` letra por letra — el nombre
  exacto puede variar según el modelo/lote del WD-1012 (mayúsculas,
  guiones bajos, el sufijo numérico), y a veces cambia si se
  desconecta y se vuelve a conectar en otro puerto USB. Si el archivo
  simplemente no aparece en la lista, revisa que el lector esté bien
  conectado (probar otro puerto/cable) antes de tocar `.env`.
- **La ventana no abre / otro error relacionado a Tkinter** (que no sea
  el de `DISPLAY` de arriba): instala `python3-tk` (paso 5) — es un
  paquete de sistema, no de pip, así que hace falta `apt`, no alcanza
  con `pip install`.
- **El lector USB no lee nada** (pero sí abrió el dispositivo sin
  error): revisa que cerraste sesión después del `usermod -aG input`
  (paso 6), y que el aviso `[escaner] Escuchando...` aparece en la
  consola al arrancar.
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
- **La pantalla se queda mucho rato en "Código leído, Registrando..."**:
  significa que el envío al backend no está terminando rápido — revisa
  la consola (avisa "Sin conexión..." si no hay red) y cuántos
  pendientes hay con:

  ```bash
  sqlite3 cola_local.db "SELECT COUNT(*) FROM pendientes;"
  ```

  (si no tienes `sqlite3` instalado, `sudo apt install -y sqlite3` — es
  solo para inspeccionar el archivo a mano, el terminal no lo necesita,
  usa el módulo `sqlite3` que ya viene con Python). Si el número no baja
  con el backend andando, confirma `API_URL` en `.env` y que
  `curl http://<IP-del-backend>:8000/` funciona desde la Raspberry.
- **Se registró como DUPLICADO y no debía (o al revés)**: la ventana de
  tiempo para considerar un escaneo "duplicado" se configura en el
  **backend**, no acá — variable `MINUTOS_ANTIDUPLICADO_MOVIMIENTO` en
  `backend/.env` (por defecto 5 minutos). Ajusta ese valor y reinicia el
  backend.
- **La pantalla se queda en "SIN CONEXIÓN WIFI" aunque hay red**:
  espera unos segundos — el aviso se actualiza cada
  `REVISAR_RED_SEGUNDOS` (5 por defecto), no al instante. Si sigue sin
  cambiar, prueba `nmcli -t -f STATE general` a mano en la Raspberry:
  si no dice `connected`, el problema es de la red misma (router,
  contraseña, alcance de la señal), no del terminal.
- **Al escanear un código QR de WiFi dice "✗ NO SE PUDO CONECTAR"**:
  el mensaje que se muestra es el error real de `nmcli`, casi siempre
  autoexplicativo (clave incorrecta, red fuera de alcance, etc.). Si en
  cambio no pasa nada o tarda mucho y falla siempre igual, confirma el
  permiso de sudo sin contraseña para `nmcli` (paso 9) — sin eso,
  `nmcli` se queda esperando una contraseña que nunca llega y termina
  fallando por tiempo agotado. Prueba a mano:
  `sudo nmcli device wifi connect "<red>" password "<clave>"` — si te
  pide la contraseña de `sudo`, el problema es el sudoers.
- **Escaneó un código QR de WiFi pero lo trató como si fuera una
  credencial (o al revés)**: el terminal decide según el texto:
  cualquier código que empiece con `WIFI:` se trata como configuración
  de red; cualquier otra cosa (por ejemplo el enlace de una credencial)
  se manda al backend como siempre. Si un router genera el código en un
  formato distinto (no debería, es un estándar), no va a reconocerse.

## 13. Autonomía: instalación con un solo script

Los pasos 5, 6, 7, 9 y 11 de arriba (paquetes, permisos, entorno
virtual, `.env`, sudoers, arranque automático) se pueden hacer todos de
una sola vez con `instalar_raspberry.sh` (en esta misma carpeta), pensado
para que "baste con encender el dispositivo" desde ahí en adelante:

```bash
cd ~/control-acceso/terminal
chmod +x instalar_raspberry.sh
./instalar_raspberry.sh
```

Qué hace, en orden: instala los paquetes de sistema (`apt`); agrega tu
usuario al grupo `input`; crea el entorno virtual e instala las
dependencias de Python; crea `.env` a partir de
`.env.raspberry.example` **si todavía no existe** (nunca pisa uno que ya
tengas configurado); configura los permisos de sudo sin contraseña para
apagado y WiFi; activa el autologin de escritorio (`raspi-config`, así
la sesión gráfica que necesita el servicio systemd está siempre abierta
sin que nadie inicie sesión a mano); e instala y habilita el servicio
`control-acceso-terminal.service`.

Es seguro volver a correrlo si algo falla a mitad de camino — cada paso
revisa si ya está hecho antes de repetirlo. Al final:

1. Confirma (o edita) `.env` — como mínimo `API_URL` y
   `SCANNER_DEVICE_PATH` (ver paso 6) necesitan tu red y tu lector
   reales, el script no puede adivinarlos.
2. Reinicia: `sudo reboot`.

Desde ese reinicio, el dispositivo debería arrancar solo directo en el
terminal, en pantalla completa, sin teclado ni inicio de sesión manual —
y si al encender no encuentra la red que tenía, la propia pantalla
ofrece escanear un QR de otra red o continuar sin conexión (ver la
sección "WiFi de respaldo" más arriba), así que tampoco hace falta que
alguien la conecte a internet a mano.

## 14. Los archivos exactos que necesita la Raspberry

El repositorio completo trae de todo (backend, frontend, carcasa, y
también `leer_qr.py`, el terminal de **PC** para probar sin Raspberry).
La Raspberry **no necesita nada de eso** — solo esta lista, todos dentro
de `terminal/`:

```
comun.py
escaner_teclado.py
cola_local.py
red.py
leer_qr_raspberry.py
requirements-raspberry.txt
.env.raspberry.example
control-acceso-terminal.service
instalar_raspberry.sh
README_RASPBERRY.md
```

**NO hace falta copiar** (son solo para el terminal de PC o para
desarrollo): `leer_qr.py`, `requirements.txt`, `.env.example`,
`README.md`, ni ninguna carpeta de `backend/`, `frontend/` o `carcasa/`.

Si copiás el repositorio entero con `git clone` (paso 4.2), no pasa nada
con tener los archivos de más — simplemente no se usan. Esta lista sirve
sobre todo para la alternativa sin GitHub del paso 4.3 (copiar por `scp`
sin clonar todo el repositorio): copiando solo estos archivos alcanza
para que el terminal funcione completo, con la cola local, el envío
asíncrono, la marca duplicada y el WiFi de respaldo incluidos.

## Ver también

- `../backend/README.md` — endpoints de latido/apagado/encendido.
- `../carcasas/` — carcasa donde va montado todo esto.
- `../backend/README.md` — cómo levantar el backend.
