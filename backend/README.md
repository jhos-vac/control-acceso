# Backend — Sistema de Control de Acceso

API en FastAPI + PostgreSQL para el registro de entradas y salidas
mediante código QR, según la propuesta técnica del proyecto.

## Estructura

```
backend/
├── app/
│   ├── __init__.py
│   ├── database.py    # conexión a PostgreSQL (SQLAlchemy)
│   ├── models.py       # tablas: personal, movimientos, puntos_acceso, usuarios
│   ├── schema.py        # esquemas Pydantic (entrada/salida de la API)
│   ├── services.py     # lógica de negocio (QR, ENTRADA/SALIDA, login)
│   ├── routes.py       # endpoints /api/...
│   └── main.py           # arranque de la app FastAPI
├── seed_db.py           # crea usuario admin + punto de acceso inicial
├── requirements.txt
└── .env.example
```

## 1. Requisitos previos

- Python 3.11+ (ya tienes un entorno virtual creado en `.venv`)
- PostgreSQL instalado y corriendo localmente (o accesible por red)

## 2. Preparar el entorno

```bash
cd backend
# activar el entorno virtual (Windows PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## 3. Crear la base de datos en PostgreSQL

Desde `psql` o una herramienta como pgAdmin/DBeaver:

```sql
CREATE DATABASE control_acceso;
```

## 4. Configurar variables de entorno

```bash
copy .env.example .env
```

Edita `.env` y ajusta `DATABASE_URL` con tu usuario/password de
PostgreSQL, y genera un `SECRET_KEY` propio.

## 5. Crear las tablas y datos iniciales

Las tablas se crean automáticamente al arrancar la API (`main.py`
llama a `Base.metadata.create_all`), pero para tener un usuario admin
y un punto de acceso desde el inicio, corre:

```bash
python seed_db.py
```

Esto crea el usuario `admin` (ver `.env` para la contraseña) y un
punto de acceso llamado "Entrada principal".

## 6. Levantar la API

```bash
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Documentación interactiva (Swagger): http://127.0.0.1:8000/docs

## 7. Probar el flujo principal

1. Login para obtener un token (para usar los endpoints de consulta):

   ```
   POST /api/login
   { "usuario": "admin", "password": "admin123" }
   ```

2. Simular una lectura de QR (no requiere token, es lo que usa el
   terminal/lector — ver `../terminal/`):

   ```
   POST /api/acceso
   {
     "qr": "https://its.academicok.com/datoscredencial?idperfil=12345",
     "punto_acceso": 1
   }
   ```

   El backend busca primero la persona localmente por `idperfil`; si no
   la encuentra, consulta AcademicOK (`services.consultar_fuente_institucional`,
   ya implementado — hace scraping de la página pública `datoscredencial`
   con el `idperfil` real, igual que la prueba de concepto). Si tampoco
   la encuentra ahí, responde `DENEGADO`. Para probar con un `idperfil`
   real necesitas uno válido en AcademicOK; con uno inventado, el
   resultado esperado es `DENEGADO`.

3. Repetir la misma llamada con un `idperfil` que sí exista: la segunda
   vez debería registrar SALIDA en lugar de ENTRADA (regla validada:
   última lectura determina el tipo de movimiento).

## Pendientes conocidos (ver documento técnico, sección 13)

- Confirmar con TI si existe/existirá una API oficial de AcademicOK que
  reemplace el scraping actual de `datoscredencial`
  (`services.consultar_fuente_institucional` es el único lugar a tocar
  cuando eso pase).
- Migrar la creación de tablas a Alembic cuando el esquema empiece a
  cambiar con frecuencia.
- Restringir `allow_origins` de CORS en `main.py` al dominio real del
  panel React antes de pasar a producción.
- Endpoint(s) de administración de `personal` y `usuarios` (alta/baja)
  para el panel administrativo — por ahora el foco fue el flujo de
  acceso y la base de datos.
