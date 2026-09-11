# Sistema de Control de Acceso

Registro de entradas y salidas mediante código QR (ver
`Resumen_y_Propuesta_Sistema_Control_de_Acceso.docx` para la propuesta
completa).

## Componentes

| Carpeta | Qué es | Cómo se ejecuta |
| --- | --- | --- |
| `backend/` | API (FastAPI + PostgreSQL). Toda la lógica: identificar personas, consultar AcademicOK, decidir ENTRADA/SALIDA, autenticación. | `uvicorn app.main:app --reload` |
| `frontend/` | Panel administrativo (React). Dashboard, registros, personas, puntos de acceso. | `npm run dev` |
| `terminal/` | Lector de QR de prueba en PC (cámara + OpenCV). Solo lee el QR y llama a la API — el equivalente de lo que hará la Raspberry Pi. | `python leer_qr.py` |

Cada carpeta tiene su propio `README.md` con instrucciones detalladas.

## Arranque rápido (todo de una vez)

```
.\iniciar.ps1
```

(clic derecho -> "Ejecutar con PowerShell", o desde una terminal PowerShell
parado en esta carpeta). Crea los entornos virtuales que falten, instala
dependencias, levanta el backend y el frontend cada uno en su propia
ventana, y abre la cámara para leer QR en la ventana actual. La primera
vez tarda más (instala todo); después es rápido. Requiere que PostgreSQL
ya esté instalado y la base `control_acceso` creada (ver `backend/README.md`,
paso 3) — eso el script no lo hace por ti.

## Orden para levantar todo a mano

1. `backend/` — crear la base en PostgreSQL, instalar dependencias,
   copiar `.env.example` a `.env`, correr `seed_db.py` y luego
   `uvicorn app.main:app --reload`.
2. `frontend/` — `npm install`, copiar `.env.example` a `.env`,
   `npm run dev`. Entrar con el usuario que creó `seed_db.py`.
3. `terminal/` — `pip install -r requirements.txt`, copiar
   `.env.example` a `.env`, `python leer_qr.py` (con el backend ya
   corriendo).

## Flujo de datos

```
Cámara (terminal/leer_qr.py)
     │  POST /api/acceso {qr, punto_acceso}
     ▼
Backend (backend/app/services.py::procesar_acceso)
     │  1. busca a la persona local por idperfil
     │  2. si no está, consulta AcademicOK (scraping de datoscredencial)
     │  3. si tampoco está ahí → DENEGADO
     │  4. si está → determina ENTRADA/SALIDA y lo guarda
     ▼
PostgreSQL (tablas: personal, movimientos, puntos_acceso, usuarios)
     ▲
     │  GET /api/personas, /api/movimientos, /api/personas/dentro...
     │
Frontend (frontend/, panel administrativo)
```
