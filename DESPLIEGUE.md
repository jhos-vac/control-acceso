# Despliegue en producción — `control-acceso.sudamericano.edu.ec`

Guía para poner el sistema en el servidor de la nube, con ese subdominio.
Asume un servidor Linux (Ubuntu/Debian) con acceso `sudo` y el DNS del
subdominio ya apuntando a la IP del servidor (eso lo gestiona quien
administra el dominio `sudamericano.edu.ec` — sin eso, `certbot` del
paso 6 no va a poder emitir el certificado).

## Qué se instala y dónde

| Parte | Versión | Qué hace |
| --- | --- | --- |
| Python | 3.11+ | Corre el backend |
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
sudo -u postgres psql -c "CREATE DATABASE control_acceso;"
sudo -u postgres psql -c "CREATE USER control_acceso_app WITH PASSWORD 'ELEGIR_UNA_CONTRASEÑA';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE control_acceso TO control_acceso_app;"
```

Usa esa contraseña en `DATABASE_URL` del `.env` del backend (paso 4).

## 3. Clonar el proyecto

```bash
sudo mkdir -p /var/www/control-acceso
sudo chown $USER:$USER /var/www/control-acceso
git clone <URL-DEL-REPOSITORIO> /var/www/control-acceso
```

(Mientras no esté confirmado el repositorio de GitHub real de este
proyecto — ver `claude/Terminal_QR_y_AcademicOK_Estado.md` — se puede
copiar el proyecto por `scp`/`rsync` en vez de `git clone`, igual que se
viene haciendo con la Raspberry.)

## 4. Backend

```bash
cd /var/www/control-acceso/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.production.example .env
nano .env   # completar DATABASE_URL, SECRET_KEY, ADMIN_PASSWORD (ver comentarios del archivo)
python seed_db.py   # crea el usuario administrador inicial
deactivate
```

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
npm install
cp .env.production.example .env.production
npm run build
```

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
curl https://control-acceso.sudamericano.edu.ec/                # {"status":"ok",...}
curl https://control-acceso.sudamericano.edu.ec/api/personas     # 401 (requiere token) -- ya es buena señal, contestó la API
```

Y entrar al panel desde el navegador: `https://control-acceso.sudamericano.edu.ec`
con el usuario que creó `seed_db.py`.

## 8. Terminal (Raspberry Pi u otro lector)

Ya no necesita estar en la misma red que el backend — solo internet.
En su `.env` (ver `terminal/.env.raspberry.example`, ya actualizado):

```
API_URL=https://control-acceso.sudamericano.edu.ec
```

(sin `/api` al final — el terminal ya lo agrega solo).

## Actualizar el sistema más adelante

```bash
cd /var/www/control-acceso
git pull   # o volver a copiar los archivos que cambiaron

cd backend && source .venv/bin/activate && pip install -r requirements.txt && deactivate
sudo systemctl restart control-acceso-backend.service

cd ../frontend && npm install && npm run build   # Nginx sirve el dist/ nuevo solo, sin reiniciar nada
```

## Seguridad — checklist antes de dar por terminado el despliegue

- [ ] `SECRET_KEY` del backend es una clave generada de verdad, no la de
      desarrollo ni la de este ejemplo.
- [ ] Se cambió la contraseña del usuario `admin` desde el panel (la
      de `ADMIN_PASSWORD`/`seed_db.py` es solo para el primer ingreso).
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
