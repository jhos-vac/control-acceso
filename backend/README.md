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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://127.0.0.1:8000
- Documentación interactiva (Swagger): http://127.0.0.1:8000/docs

**`--host 0.0.0.0` es importante** si algún otro equipo de la red va a
hablar con este backend (el terminal de Raspberry Pi, el frontend desde
otra PC, o probar desde el celular) — sin eso, `uvicorn` por defecto
solo escucha conexiones que vienen de la misma máquina (`127.0.0.1`), y
cualquier otro dispositivo que intente conectarse se queda esperando
hasta que la conexión da timeout (`Connection ... timed out`), aunque la
IP y el puerto en su `.env`/`API_URL` estén bien escritos.

Si después de este cambio otro equipo sigue sin poder conectarse,
revisa también el **Firewall de Windows**: puede estar bloqueando
conexiones entrantes al puerto 8000. La primera vez que corres
`uvicorn` con `--host 0.0.0.0`, Windows normalmente pregunta si permitir
el acceso — dile que sí, para redes privadas. Si no te preguntó (o
dijiste que no sin querer), agrega la regla a mano: *Firewall de Windows
Defender* → *Configuración avanzada* → *Reglas de entrada* → *Nueva
regla* → Puerto → TCP → `8000` → Permitir la conexión.

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

4. Repetir la misma llamada una tercera vez, enseguida: en vez de volver
   a alternar a ENTRADA, debería responder `DUPLICADO` (ver sección
   siguiente) — no se registra un movimiento nuevo.

## Marca duplicada (alguien no está seguro si ya marcó)

Si una persona ya tiene un movimiento registrado hace menos de
`MINUTOS_ANTIDUPLICADO_MOVIMIENTO` (`.env`, por defecto 5 minutos), un
nuevo escaneo **no alterna** a ENTRADA/SALIDA — responde:

```json
{
  "resultado": "DUPLICADO",
  "mensaje": "Ya se había registrado ENTRADA hace 2 min -- no se volvió a marcar para evitar un duplicado.",
  "persona": { ... },
  "fecha_hora": "2026-09-16T08:30:00",
  "ultimo_tipo": "ENTRADA"
}
```

No se crea ningún `Movimiento` nuevo en ese caso — el historial y los
reportes quedan limpios, sin marcas duplicadas de una misma persona por
error. `ultimo_tipo` le sirve al terminal para mostrar qué fue lo que ya
se había registrado.

### `fecha_hora_cliente` — por qué `POST /api/acceso` acepta una fecha

El terminal puede mandar, junto con el QR, el momento **real** en que lo
leyó (`fecha_hora_cliente`, opcional). Es necesario para que la cola
local sin conexión del terminal de Raspberry Pi (ver
`../terminal/README_RASPBERRY.md`) funcione bien: si el terminal estuvo
sin red un rato y recién puede enviar lo acumulado minutos u horas
después, cada acceso debe evaluarse (orden ENTRADA/SALIDA, ventana de
duplicado) con la hora en que realmente se escaneó, no con la hora en
que llegó al backend. Si no se manda, o si el backend la considera poco
creíble (más de 2 minutos en el futuro, o más de 30 días en el pasado —
señal de que el reloj del terminal está mal), se usa la hora del
servidor.

## Migraciones (sin Alembic todavía)

`Base.metadata.create_all` (ver `main.py`) solo crea las **tablas** que
falten. Cuando una tabla ya existe pero el modelo le agrega columnas
nuevas (como pasó con el latido/estado en línea, y ahora con la MAC para
encender a distancia), **ya no hace falta correr `ALTER TABLE` a mano**:
`database.py` tiene una función `asegurar_columnas_nuevas()` que se llama
sola al arrancar el backend (`main.py`) y agrega cualquier columna que
falte. Si alguna vez hace falta correrlo a mano de todos modos (por
ejemplo, para revisar qué agregó), el equivalente en SQL es:

```sql
ALTER TABLE puntos_acceso ADD COLUMN IF NOT EXISTS ultimo_latido TIMESTAMP NULL;
ALTER TABLE puntos_acceso ADD COLUMN IF NOT EXISTS comando_pendiente VARCHAR(20) NULL;
ALTER TABLE puntos_acceso ADD COLUMN IF NOT EXISTS mac_address VARCHAR(17) NULL;
```

## Encender un punto de acceso a distancia (Wake-on-LAN)

Además de "Apagar", el panel tiene un botón "Encender" para un punto de
acceso que está sin conexión. Funciona mandando un paquete Wake-on-LAN
(`services.enviar_wol`) a la dirección MAC configurada en ese punto de
acceso (se edita desde el panel, botón "Editar" en cada tarjeta). Antes
de confiar en esto, hay que saber que **no siempre es posible**:

- Necesita que el equipo tenga Wake-on-LAN habilitado en el BIOS/UEFI, y
  casi siempre estar conectado por **cable** (no WiFi).
- El paquete se manda por broadcast en la red local — por defecto a
  `255.255.255.255`. Si el backend y el terminal NO están en la misma
  red/subred, hay que configurar `WOL_BROADCAST_IP` en el `.env` con la
  dirección de broadcast dirigido de la red del terminal (ej.
  `192.168.1.255`); cruzar routers sin eso normalmente no funciona.
- **Una Raspberry Pi apagada por lo general NO se puede encender así**
  (a diferencia de una PC de escritorio, no mantiene la placa de red con
  energía en espera). Como el terminal final del proyecto será una
  Raspberry Pi, este botón es sobre todo útil para la PC de pruebas
  actual; para la Pi en producción, la alternativa realista es un
  enchufe/relé inteligente que corte y reponga la energía física.

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
