# Terminal QR (prueba en PC)

Script de prueba que usa la cámara de tu computadora para leer el QR de
la credencial y registrar el acceso llamando al backend. Es el mismo
papel que cumple el terminal de producción en Raspberry Pi (ver
`README_RASPBERRY.md`): **solo lee el QR y muestra el resultado**, toda
la lógica (buscar en la base local, consultar AcademicOK si hace falta,
decidir ENTRADA/SALIDA) vive en el backend.

> **¿Buscas la guía de la Raspberry Pi?** Este documento es solo para el
> terminal de prueba en PC (webcam). Para el terminal de producción
> (Raspberry Pi 4, cámara del módulo + lector QR USB de mesa a la vez,
> apagado/encendido remoto, arranque automático), ver
> **`README_RASPBERRY.md`**. La lógica de comunicación con el backend
> (latido, apagado, banner de resultado) vive en `comun.py` y la
> comparten los dos terminales — no está duplicada.

## 1. Instalar dependencias

Recomendado: un entorno virtual propio, separado del `backend/.venv`
(para no mezclar `opencv-python`, que no hace falta en el servidor,
con las dependencias del backend).

```bash
cd terminal
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Configurar

```bash
copy .env.example .env
```

Por defecto asume que el backend corre en `http://127.0.0.1:8000` y que
existe el punto de acceso `id=1` (el que crea `seed_db.py` del backend,
"Entrada principal"). Ajusta `.env` si tu backend corre en otra
máquina/puerto, o si quieres usar otro punto de acceso.

## 3. Ejecutar

Con el backend corriendo (`uvicorn app.main:app --reload` desde
`backend/`):

```bash
python leer_qr.py
```

Se abre la ventana de la cámara. Al detectar un QR válido, se envía al
backend (`POST /api/acceso`) y se muestra en pantalla:

- **Verde** — ENTRADA registrada
- **Ámbar** — SALIDA registrada
- **Rojo** — acceso DENEGADO (no se pudo identificar a la persona, ni
  localmente ni en AcademicOK)
- **Gris** — error de conexión con el backend

Controles: `R` fuerza una nueva lectura del mismo QR antes de que pase
el tiempo antiduplicado; `ESC` cierra el programa.

## Latido (estado en línea) y apagado remoto

Mientras corre, este script manda un "latido" al backend cada
`INTERVALO_LATIDO` segundos (`POST /api/puntos-acceso/{id}/latido`). Es
lo que permite que el panel muestre si el dispositivo está encendido o
apagado (icono de notificaciones y la página "Puntos de acceso").

Si un usuario ADMIN aprieta "Apagar dispositivo" en el panel, el
backend deja esa orden guardada; este script la recoge en su próximo
latido (máximo `INTERVALO_LATIDO` segundos de demora) y apaga el
equipo:

- **Windows** (la PC de pruebas actual): corre `shutdown /s /t 5` —
  **apaga toda la PC**, no solo este script. Ten esto presente si estás
  probando en tu propia computadora de desarrollo.
- **Linux** (pensado para cuando esto corra en una Raspberry Pi): corre
  `sudo shutdown -h now`. El usuario que ejecuta el script necesita
  permiso para apagar sin que se le pida contraseña — en Raspberry Pi
  OS esto ya viene configurado por defecto para el usuario `pi`; en
  otro caso hay que agregar una regla en `sudoers` (`NOPASSWD` para
  `/sbin/shutdown`).

Si por algún motivo no se puede apagar solo (permisos, comando no
disponible), el script lo avisa por consola y hay que apagar el equipo
a mano.

## Notas

- La consulta a AcademicOK (scraping de `datoscredencial`) vive en
  `backend/app/services.py::consultar_fuente_institucional` — no en
  este script. Si AcademicOK cambia su página o TI confirma una API
  oficial, ese es el único lugar que hay que tocar.
- Este script no guarda nada localmente ni almacena credenciales de
  AcademicOK — solo llama al backend por HTTP, igual que hará la
  Raspberry Pi en producción (por HTTPS).
