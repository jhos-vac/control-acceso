# Despliegue en producción — `control-acceso.sudamericano.edu.ec`

Guía para poner el sistema en el servidor de la nube, con ese subdominio.
Asume un servidor Linux (Ubuntu/Debian) con acceso `sudo` y el DNS del
subdominio ya apuntando a la IP del servidor (eso lo gestiona quien
administra el dominio `sudamericano.edu.ec` — sin eso, `certbot` del
paso 6 no va a poder emitir el certificado).

## Características de la máquina virtual (para pedirla al proveedor de la nube)

Todo el sistema (backend + base de datos + panel) corre cómodo en UNA
sola VM pequeña — no es una carga pesada: es un control de acceso de
un solo edificio (algunos cientos/miles de escaneos QR al día, un
puñado de personas del panel administrativo a la vez, sin video ni
adjuntos grandes).

| Recurso | Recomendado | Mínimo si hay que ajustar presupuesto |
| --- | --- | --- |
| vCPU | 2 | 1 |
| RAM | 4 GB | 2 GB |
| Disco | 40 GB SSD | 20 GB SSD |
| Sistema operativo | Ubuntu Server 22.04 o 24.04 LTS | (misma) |
| Red | 1 IP pública, sin límite de ancho de banda relevante (los pagos "1 TB/mes" de cualquier proveedor sobran de lejos) | — |

Por qué estos números:

- **2 vCPU / 4 GB** en vez de 1/2: no es porque el backend en sí pida
  mucho (Uvicorn con 2 workers, ver `deploy/control-acceso-backend.service`,
  usa poca memoria) — es para que PostgreSQL, Nginx, el backend y,
  sobre todo, el paso puntual de compilar el panel (`npm run build` en
  el paso 5 de esta guía, que puede pedir 1-2 GB de RAM mientras
  corre) convivan sin quedarse sin memoria. Con 2 GB también funciona,
  pero más ajustado — si el proveedor cobra por GB, 4 GB es la mejora
  que más se nota.
- **40 GB de disco**: el sistema (Ubuntu + Postgres + dependencias) usa
  unos 8-10 GB; el resto es margen para que la base de datos crezca
  por años (los registros de entrada/salida son filas chiquitas — para
  darte una idea, aunque se junten miles por día, tardaría mucho en
  llegar a ocupar unos pocos GB) y para logs. 20 GB alcanza igual si
  hace falta recortar.
- **Ubuntu Server LTS**: es lo que asume esta guía (`apt`, `systemctl`,
  etc.) — cualquier otra distribución basada en Debian/Ubuntu también
  funcionaría, pero los comandos exactos podrían variar.
- Nombres equivalentes en proveedores comunes (a modo de referencia, no
  es que el sistema dependa de ninguno en particular): un droplet/VM de
  "2 vCPU, 4 GB RAM" — en DigitalOcean eso es el plan Basic de $24/mes
  aprox., en AWS algo como un `t3.medium`, en Google Cloud un
  `e2-medium` — los precios cambian seguido, conviene cotizar directo
  con el proveedor elegido en vez de guiarse por esto.

Si más adelante el sistema crece a varios edificios/terminales a la
vez, conviene volver a evaluar (sobre todo la RAM y el disco de la
base de datos) — para un solo edificio, lo de arriba tiene margen de
sobra.

## Qué se instala y dónde

| Parte | Versión | Qué hace |
| --- | --- | --- |
| Python | 3.10 o superior (Ubuntu 22.04 trae 3.10, Ubuntu 24.04 trae 3.12: sirven los dos) | Corre el backend |
| PostgreSQL | 15 o 16 | Guarda toda la información (personas, movimientos, usuarios, puntos de acceso) |
| Node.js | 18 o 20 LTS | Solo para compilar el panel (`npm run build`) — no queda corriendo en producción |
| Nginx | cualquiera reciente | Sirve el panel (archivos estáticos) y hace de proxy hacia el backend |
| certbot | cualquiera reciente | Certificado TLS (HTTPS) gratis, Let's Encrypt |

El backend (FastAPI/Uvicorn) y el panel (React) quedan en el **mismo
subdominio**: el panel en `/`, la API en `/api/` — así no hace falta un
segundo registro DNS ni preocuparse por CORS entre subdominios
distintos. Ver `deploy/nginx-control-acceso.conf`.

## 1. Preparar el servidor

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv postgresql nginx git
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

## 2. Base de datos

```bash
sudo -u postgres psql -c "CREATE USER control_acceso_app WITH PASSWORD 'ELEGIR_UNA_CONTRASENA';"
sudo -u postgres psql -c "CREATE DATABASE control_acceso OWNER control_acceso_app;"
```

Usa esa contraseña en `DATABASE_URL` del `.env` del backend (paso 4). Si
la contraseña lleva caracteres especiales (`@ : / # ? %`) hay que
escribirlos codificados en la URL (por ejemplo `@` → `%40`); lo más
simple es usar una contraseña solo con letras y números.

> **Importante:** la base se crea con `OWNER control_acceso_app` (no con
> un `GRANT ALL PRIVILEGES` aparte). Desde PostgreSQL 15 el esquema
> `public` ya no permite crear tablas a cualquier usuario: si la base
> quedara a nombre de `postgres`, el backend fallaría al arrancar con
> `permission denied for schema public` aunque el usuario tenga "todos los
> privilegios" sobre la base.

## 3. Clonar el proyecto

```bash
sudo mkdir -p /var/www/control-acceso
sudo chown $USER:$USER /var/www/control-acceso
git clone https://github.com/jhos-vac/control-acceso.git /var/www/control-acceso
```

Si el repositorio es **privado**, `git clone` por HTTPS pedirá usuario y
contraseña y va a fallar en un servidor sin interfaz. En ese caso hay que
darle al servidor una *deploy key* (solo lectura): en el servidor
`ssh-keygen -t ed25519 -C "deploy-control-acceso"`, pegar la llave
pública (`~/.ssh/id_ed25519.pub`) en GitHub → repositorio → *Settings* →
*Deploy keys*, y clonar con la URL SSH
(`git@github.com:jhos-vac/control-acceso.git`).

## 4. Backend

```bash
cd /var/www/control-acceso/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.production.example .env
chmod 600 .env   # tiene la contraseña de la base y la clave de firma: que solo lo lea este usuario
nano .env   # completar DATABASE_URL, SECRET_KEY, TERMINAL_API_KEY, ADMIN_PASSWORD (ver comentarios del archivo)
python seed_db.py   # crea las tablas y el usuario administrador inicial
deactivate
```

`APP_ENV=production` (ya viene en la plantilla) hace que el backend **se
niegue a arrancar** si `SECRET_KEY`, `ALLOWED_ORIGINS` o `DATABASE_URL`
siguen con los valores de ejemplo — el error queda en
`journalctl -u control-acceso-backend` y dice qué falta. Las claves se
generan así:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"   # SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(24))"   # TERMINAL_API_KEY
```

`TERMINAL_API_KEY` es la clave que deben mandar los terminales
(Raspberry) — sin ella, cualquiera que conozca la URL podría falsificar
entradas y salidas. Va igual en `API_KEY` del `.env` de cada terminal
(paso 8).

`ALLOWED_ORIGINS` ya viene en la plantilla apuntando a
`https://control-acceso.sudamericano.edu.ec` — así el panel solo puede
llamar a la API desde ese dominio (antes estaba abierto a cualquiera
con `allow_origins=["*"]`, bien para desarrollo local, no para
producción).

Instalar y arrancar el servicio (queda escuchando solo en
`127.0.0.1:8000`, no expuesto directo a internet):

```bash
sudo cp deploy/control-acceso-backend.service /etc/systemd/system/
sudo nano /etc/systemd/system/control-acceso-backend.service   # reemplazar <USUARIO>
sudo systemctl daemon-reload
sudo systemctl enable --now control-acceso-backend.service
sudo systemctl status control-acceso-backend.service
```

## 5. Frontend (panel/dashboard)

```bash
cd /var/www/control-acceso/frontend
npm ci
npm run build
```

No hace falta ningún `.env.production`: sin él, el panel usa rutas
relativas (`/api/...`) al mismo dominio, que es justo cómo se despliega
(ver `src/api/client.js`). Solo créalo (copiando
`.env.production.example`) si algún día el panel y la API quedan en
dominios distintos.

Esto genera `frontend/dist/` — son los archivos estáticos que sirve
Nginx (el `nginx-control-acceso.conf` del paso 6 ya apunta ahí).

## 6. Nginx + HTTPS

```bash
sudo cp deploy/nginx-control-acceso.conf /etc/nginx/sites-available/control-acceso
sudo ln -s /etc/nginx/sites-available/control-acceso /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d control-acceso.sudamericano.edu.ec
```

`certbot` edita el archivo de Nginx solo para agregar el bloque HTTPS
(puerto 443 + certificado) y el redirect de `http://` a `https://` — no
hace falta tocar nada a mano ahí.

## 7. Probar

```bash
curl https://control-acceso.sudamericano.edu.ec/api/health      # {"status":"ok",...}  -> backend vivo Y conectado a la base
curl -i https://control-acceso.sudamericano.edu.ec/api/personas  # 401 (requiere token) -- ya es buena señal, contestó la API
```

(`/` no sirve para probar el backend: ahí Nginx entrega el panel, no la
API. Para probar todo junto: `/api/health`.) Si `/api/health` da `502`,
el backend no está corriendo: `sudo systemctl status control-acceso-backend`
y `journalctl -u control-acceso-backend -n 50`. Si da `503`, el backend
corre pero no llega a la base de datos (revisar `DATABASE_URL`).

Y entrar al panel desde el navegador: `https://control-acceso.sudamericano.edu.ec`
con el usuario que creó `seed_db.py`.

## 8. Terminal (Raspberry Pi u otro lector)

Ya no necesita estar en la misma red que el backend — solo internet.
En su `.env` (ver `terminal/.env.raspberry.example`, ya actualizado):

```
API_URL=https://control-acceso.sudamericano.edu.ec
API_KEY=<el mismo valor de TERMINAL_API_KEY del .env del backend>
```

(sin `/api` al final — el terminal ya lo agrega solo).

Si la `API_KEY` falta o no coincide, el backend responde `401` y el
terminal **no pierde ningún registro**: los QR leídos quedan en su cola
local y se envían solos en cuanto se corrige la clave. Lo mismo pasa si
el backend está reiniciándose (durante un despliegue) — el terminal
reintenta en vez de descartar.

## Actualizar el sistema más adelante

```bash
cd /var/www/control-acceso
git pull   # o volver a copiar los archivos que cambiaron

cd backend && source .venv/bin/activate && pip install -r requirements.txt && deactivate
sudo systemctl restart control-acceso-backend.service

cd ../frontend && npm ci && npm run build   # Nginx sirve el dist/ nuevo solo, sin reiniciar nada

curl https://control-acceso.sudamericano.edu.ec/api/health   # confirmar que volvió a levantar
```

Los cambios de esquema (tablas/columnas nuevas) se aplican solos al
reiniciar el backend (`app/database.py`), de forma segura aunque los dos
workers arranquen a la vez. Solo **agregan** columnas: renombrar o
eliminar columnas requiere una migración manual (o pasar a Alembic).
Hacer un respaldo antes de actualizar (`pg_dump`, ver más abajo) es la
red de seguridad si algo sale mal.

## Respaldos de la base de datos

```bash
sudo mkdir -p /var/backups/control-acceso && sudo chown $USER /var/backups/control-acceso
# Un respaldo comprimido por día, conserva los últimos 14 (cron del usuario que corre el backend):
( crontab -l 2>/dev/null; echo '30 2 * * * pg_dump -U control_acceso_app -h localhost control_acceso | gzip > /var/backups/control-acceso/control_acceso_$(date +\%F).sql.gz && find /var/backups/control-acceso -name "*.sql.gz" -mtime +14 -delete' ) | crontab -
```

`pg_dump` pide la contraseña de `control_acceso_app`; para que el cron
no se quede esperándola, guárdala en `~/.pgpass` (`chmod 600`) con el
formato `localhost:5432:control_acceso:control_acceso_app:LA_CONTRASENA`.
**Probar una restauración** (`gunzip -c archivo.sql.gz | psql ...` sobre
una base de prueba) antes de confiar en el respaldo.

## Seguridad — checklist antes de dar por terminado el despliegue

- [ ] `SECRET_KEY` del backend es una clave generada de verdad, no la de
      desarrollo ni la de este ejemplo.
- [ ] Se cambió la contraseña del usuario `administrador` desde el panel
      (la de `ADMIN_PASSWORD`/`seed_db.py` es solo para el primer
      ingreso -- el panel lo obliga de todas formas: la primera vez que
      entra lo manda a elegir una propia, ver `debe_cambiar_password`).
- [ ] `APP_ENV=production` y `TERMINAL_API_KEY` definidos en el `.env` del
      backend, y la misma clave en `API_KEY` de cada terminal.
- [ ] `backend/.env` con permisos `600` (`ls -l backend/.env`).
- [ ] Respaldo diario de PostgreSQL configurado y restauración probada.
- [ ] Desde el propio servidor, AcademicOK responde:
      `curl -s -o /dev/null -w "%{http_code}\n" "https://its.academicok.com/datoscredencial?action=consulta&id=UN_IDPERFIL_REAL"`
      (200). Es la única dependencia externa: si el proveedor de nube
      queda bloqueado por AcademicOK, las personas nuevas se denegarán.
- [ ] `ALLOWED_ORIGINS` apunta solo a `https://control-acceso.sudamericano.edu.ec`
      (no quedó en `*`).
- [ ] El backend escucha solo en `127.0.0.1` (no `0.0.0.0`) — es Nginx
      quien lo expone hacia afuera, con TLS.
- [ ] El puerto de PostgreSQL (5432) no está abierto hacia internet en
      el firewall del servidor, solo accesible localmente.
- [ ] HTTPS funcionando (candado en el navegador) — sin esto el login
      del panel viaja la contraseña sin cifrar.

## Ver también

- `deploy/nginx-control-acceso.conf`, `deploy/control-acceso-backend.service`
- `backend/README.md`, `backend/.env.production.example`
- `frontend/.env.production.example`
- `terminal/README_RASPBERRY.md` (para el terminal físico)
