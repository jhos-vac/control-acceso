# Frontend — Panel de Control de Acceso

Panel administrativo en **React + Vite + Tailwind CSS**, consumiendo la API
del backend (FastAPI). Color institucional: blanco + `#009EAD`.

## Estructura

```
frontend/
├── src/
│   ├── api/client.js         # cliente axios (adjunta el token JWT)
│   ├── context/AuthContext.jsx
│   ├── components/           # StatCard, RutaProtegida, estados de carga
│   ├── layouts/DashboardLayout.jsx  # sidebar + topbar
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx     # Resumen: tarjetas, gráfico, tiempo real
│   │   ├── Registros.jsx     # historial de movimientos
│   │   ├── Personas.jsx
│   │   └── PuntosAcceso.jsx
│   └── utils/fechas.js
├── tailwind.config.js         # color "brand" = #009EAD
└── .env.example
```

## 1. Requisitos

- Node.js 18 o superior (revisa con `node -v`; si no lo tienes instalado,
  descárgalo de https://nodejs.org).
- El backend corriendo (ver `backend/README.md`).

## 2. Instalar dependencias

```bash
cd frontend
npm install
```

## 3. Configurar la URL del backend

```bash
copy .env.example .env
```

Por defecto apunta a `http://127.0.0.1:8000` (el backend local). Ajusta
`VITE_API_URL` en `.env` si el backend corre en otra dirección.

## 4. Levantar en desarrollo

```bash
npm run dev
```

Abre http://localhost:5173 — te pedirá iniciar sesión con el usuario creado
por `seed_db.py` en el backend (por defecto `administrador` /
`administrador123`). La primera vez que entres, el panel te va a pedir
elegir tu propia contraseña antes de dejarte ver el resto (ver
"Cambiar/recuperar contraseña" más abajo) — es normal, no es un error.

## 5. Compilar para producción

```bash
npm run build
```

Genera la carpeta `dist/` lista para desplegar.

## Notas de diseño

- El layout (sidebar + tarjetas + gráfico + panel "en tiempo real") está
  inspirado en las referencias que compartiste, adaptado al color
  institucional `#009EAD` sobre fondo blanco.
- El gráfico de "Actividad de la semana" y las tarjetas se calculan en el
  navegador a partir de `GET /api/movimientos`, `GET /api/personas` y
  `GET /api/personas/dentro` — no requieren endpoints nuevos en el backend.
- Si el token expira o es inválido, la sesión se cierra automáticamente y
  se redirige a `/login`.

## Cambiar / recuperar contraseña

- **Cambiar la propia contraseña**: ícono de llave junto al nombre de
  usuario, abajo del todo en la barra lateral (`src/pages/CambiarPassword.jsx`,
  `POST /api/usuarios/me/password`) — pide la contraseña actual.
- **Primer ingreso / después de un reseteo**: la misma pantalla, pero
  obligatoria — no se puede usar el resto del panel hasta elegir una
  contraseña propia (`usuario.debe_cambiar_password`, ver `RutaProtegida.jsx`).
- **Un ADMIN resetea la contraseña de otro usuario** que quedó afuera:
  `POST /api/usuarios/{id}/resetear-password` (todavía no tiene botón en
  el panel — hoy se llama directo a la API; agregar la pantalla de
  administración de usuarios lo resolvería, ver "Pendiente").
- **El propio ADMIN se queda afuera** (olvidó su contraseña y no hay
  quien se la resetee desde el panel): `backend/resetear_password_admin.py`,
  un script para correr directo en el servidor — ver `backend/README.md`.

## Pendiente

- Página de administración de `usuarios` (alta/edición/reseteo de
  contraseña desde la interfaz, no solo por API) — por ahora el usuario
  admin se crea desde `seed_db.py` en el backend.
- Edición/baja de personas y puntos de acceso (hoy solo hay alta de puntos
  de acceso).
- Vista específica para el terminal QR (la sección 9 del documento técnico
  la describe como una pantalla aparte, pensada para la Raspberry Pi, no
  para este panel administrativo).
