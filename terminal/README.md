# Terminal QR (prueba en PC)

Script de prueba que usa la cámara de tu computadora para leer el QR de
la credencial y registrar el acceso llamando al backend. Es el mismo
papel que cumplirá más adelante la Raspberry Pi (sección 10 del
documento técnico): **solo lee el QR y muestra el resultado**, toda la
lógica (buscar en la base local, consultar AcademicOK si hace falta,
decidir ENTRADA/SALIDA) vive en el backend.

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

## Notas

- La consulta a AcademicOK (scraping de `datoscredencial`) vive en
  `backend/app/services.py::consultar_fuente_institucional` — no en
  este script. Si AcademicOK cambia su página o TI confirma una API
  oficial, ese es el único lugar que hay que tocar.
- Este script no guarda nada localmente ni almacena credenciales de
  AcademicOK — solo llama al backend por HTTP, igual que hará la
  Raspberry Pi en producción (por HTTPS).
