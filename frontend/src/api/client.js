import axios from "axios";

// URL base del backend. En desarrollo (npm run dev) cae a localhost si no hay
// .env. En el build de producción, si VITE_API_URL no está definida se usa el
// MISMO origen ("" = rutas relativas, /api/...), que es como se despliega
// (panel y API bajo el mismo subdominio, ver deploy/nginx-control-acceso.conf):
// así el build funciona igual desde un CI (GitHub Actions) sin necesitar un
// .env.production, y sin quedar apuntando a 127.0.0.1 por error.
const API_URL =
  import.meta.env.VITE_API_URL ?? (import.meta.env.PROD ? "" : "http://127.0.0.1:8000");

export const api = axios.create({
  baseURL: API_URL,
});

// Adjunta el token guardado (si existe) a cada request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Si el token expiró o es inválido, se limpia la sesión y se manda
// a /login. AuthContext escucha este evento.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("usuario");
      window.dispatchEvent(new Event("auth:expired"));
    }
    return Promise.reject(error);
  }
);

export default api;
