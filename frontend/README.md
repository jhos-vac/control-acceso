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
por `seed_db.py` en el backend (por defecto `admin` / `admin123`).

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

## Pendiente

- Páginas de administración de `usuarios` (alta/edición) — por ahora el
  usuario admin se crea desde `seed_db.py` en el backend.
- Edición/baja de personas y puntos de acceso (hoy solo hay alta de puntos
  de acceso).
- Vista específica para el terminal QR (la sección 9 del documento técnico
  la describe como una pantalla aparte, pensada para la Raspberry Pi, no
  para este panel administrativo).
