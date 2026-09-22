import React, { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Bell,
  Calendar,
  DoorOpen,
  FileBarChart,
  KeyRound,
  LayoutGrid,
  LogOut,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import api from "../api/client.js";

// Cada cuánto se refresca el estado de los puntos de acceso para el
// icono de notificaciones (igual de frecuente que el latido del
// terminal, ver terminal/leer_qr.py -> INTERVALO_LATIDO).
const INTERVALO_REFRESCO_MS = 15000;

// El aviso de "reporte listo" no cambia segundo a segundo (el backend
// solo genera uno nuevo una vez al día), así que se consulta con menos
// frecuencia que el estado de los dispositivos.
const INTERVALO_NOTIFICACIONES_MS = 60000;

function tiempoRelativo(fechaIso) {
  const segundos = Math.max(0, (Date.now() - new Date(fechaIso).getTime()) / 1000);
  if (segundos < 60) return "hace un momento";
  const minutos = Math.floor(segundos / 60);
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;
  const dias = Math.floor(horas / 24);
  return `hace ${dias} d`;
}

const navItems = [
  { to: "/", label: "Resumen", icon: LayoutGrid, end: true },
  { to: "/registros", label: "Registros", icon: Calendar },
  { to: "/personas", label: "Personas", icon: Users },
  { to: "/puntos-acceso", label: "Puntos de acceso", icon: DoorOpen },
  { to: "/reportes", label: "Reportes", icon: FileBarChart },
];

const hoy = new Date().toLocaleDateString("es-EC", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

function NotificacionesDropdown() {
  const navigate = useNavigate();

  const [puntos, setPuntos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const [notificaciones, setNotificaciones] = useState([]);
  const [cargandoNotifs, setCargandoNotifs] = useState(true);

  const [abierto, setAbierto] = useState(false);
  const [pestana, setPestana] = useState("avisos"); // "avisos" | "dispositivos"
  const contenedorRef = useRef(null);

  async function cargarPuntos() {
    try {
      const { data } = await api.get("/api/puntos-acceso");
      setPuntos(data);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail || "No se pudo consultar el estado.");
    } finally {
      setCargando(false);
    }
  }

  async function cargarNotificaciones() {
    try {
      const { data } = await api.get("/api/notificaciones", { params: { limite: 10 } });
      setNotificaciones(data);
    } catch (err) {
      // si falla, simplemente no se muestran avisos — no bloquea el resto del panel
    } finally {
      setCargandoNotifs(false);
    }
  }

  useEffect(() => {
    cargarPuntos();
    const intervalo = setInterval(cargarPuntos, INTERVALO_REFRESCO_MS);
    return () => clearInterval(intervalo);
  }, []);

  useEffect(() => {
    cargarNotificaciones();
    const intervalo = setInterval(cargarNotificaciones, INTERVALO_NOTIFICACIONES_MS);
    return () => clearInterval(intervalo);
  }, []);

  // Cierra el menú al hacer clic afuera
  useEffect(() => {
    function alClicAfuera(e) {
      if (contenedorRef.current && !contenedorRef.current.contains(e.target)) {
        setAbierto(false);
      }
    }
    document.addEventListener("mousedown", alClicAfuera);
    return () => document.removeEventListener("mousedown", alClicAfuera);
  }, []);

  async function marcarLeidaYVerReporte(notif) {
    setNotificaciones((prev) =>
      prev.map((n) => (n.id === notif.id ? { ...n, leida: true } : n))
    );
    setAbierto(false);
    if (notif.desde && notif.hasta) {
      navigate(`/reportes?desde=${notif.desde}&hasta=${notif.hasta}`);
    }
    try {
      await api.post(`/api/notificaciones/${notif.id}/leer`);
    } catch (err) {
      // no crítico: si falla, la próxima carga la vuelve a mostrar como no leída
    }
  }

  const desconectados = puntos.filter((p) => !p.en_linea);
  const noLeidas = notificaciones.filter((n) => !n.leida);
  const hayAlgunaAlerta =
    (!cargando && !error && desconectados.length > 0) || noLeidas.length > 0;

  return (
    <div className="relative" ref={contenedorRef}>
      <button
        onClick={() => setAbierto((v) => !v)}
        className="relative text-slate-400 hover:text-slate-600"
        title="Notificaciones"
      >
        <Bell size={19} />
        {hayAlgunaAlerta && (
          <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-red-500" />
        )}
      </button>

      {abierto && (
        <div className="absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-xl shadow-lg z-20 overflow-hidden">
          <div className="flex border-b border-slate-100">
            <button
              onClick={() => setPestana("avisos")}
              className={`flex-1 px-4 py-2.5 text-xs font-semibold transition-colors relative ${
                pestana === "avisos"
                  ? "text-brand-700 border-b-2 border-brand"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Avisos
              {noLeidas.length > 0 && (
                <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full bg-red-500 text-white text-[10px]">
                  {noLeidas.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setPestana("dispositivos")}
              className={`flex-1 px-4 py-2.5 text-xs font-semibold transition-colors ${
                pestana === "dispositivos"
                  ? "text-brand-700 border-b-2 border-brand"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Dispositivos
              {desconectados.length > 0 && !cargando && !error && (
                <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full bg-red-500 text-white text-[10px]">
                  {desconectados.length}
                </span>
              )}
            </button>
          </div>

          {pestana === "avisos" ? (
            <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
              {cargandoNotifs ? (
                <p className="text-sm text-slate-500 px-4 py-4">Cargando...</p>
              ) : notificaciones.length === 0 ? (
                <p className="text-sm text-slate-500 px-4 py-4">
                  Todavía no hay avisos. Aquí aparecerá el reporte diario cuando
                  esté listo.
                </p>
              ) : (
                notificaciones.map((n) => (
                  <button
                    key={n.id}
                    onClick={() => marcarLeidaYVerReporte(n)}
                    className="w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-slate-50 transition-colors"
                  >
                    <span
                      className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${
                        n.leida ? "bg-slate-300" : "bg-brand"
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <p
                        className={`text-sm truncate ${
                          n.leida ? "text-slate-600" : "text-slate-900 font-semibold"
                        }`}
                      >
                        {n.titulo}
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5">{n.mensaje}</p>
                      <p className="text-[11px] text-slate-400 mt-1">
                        {tiempoRelativo(n.fecha_creacion)} · Ver reporte
                      </p>
                    </div>
                  </button>
                ))
              )}
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
              {cargando ? (
                <p className="text-sm text-slate-500 px-4 py-4">Cargando...</p>
              ) : error ? (
                <p className="text-sm text-red-600 px-4 py-4">{error}</p>
              ) : puntos.length === 0 ? (
                <p className="text-sm text-slate-500 px-4 py-4">
                  No hay puntos de acceso registrados todavía.
                </p>
              ) : (
                puntos.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      setAbierto(false);
                      navigate(`/puntos-acceso?destacar=${p.id}`);
                    }}
                    className="w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-slate-50 transition-colors"
                  >
                    <span
                      className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${
                        p.en_linea ? "bg-emerald-500" : "bg-slate-300"
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-slate-900 truncate">
                        {p.nombre}
                      </p>
                      <p className="text-xs text-slate-500">
                        {p.en_linea
                          ? "Encendido · ir al dispositivo"
                          : "Apagado / sin conexión · ir al dispositivo"}
                      </p>
                    </div>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function DashboardLayout() {
  const { usuario, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex bg-[#F7F8F8]">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 border-r border-slate-200 bg-white flex flex-col">
        <div className="h-16 flex items-center gap-2 px-6 border-b border-slate-100">
          <div className="w-8 h-8 rounded-lg bg-brand flex items-center justify-center">
            <ShieldCheck className="text-white" size={18} />
          </div>
          <span className="font-bold text-slate-900 tracking-tight">
            Control de Acceso
          </span>
        </div>

        <nav className="flex-1 px-3 py-6 space-y-1">
          <p className="px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Panel
          </p>
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-50"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-slate-100">
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg">
            <div className="w-9 h-9 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-sm font-semibold">
              {(usuario?.nombre || usuario?.usuario || "?").slice(0, 2).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-900 truncate">
                {usuario?.nombre || usuario?.usuario}
              </p>
              <p className="text-xs text-slate-500 truncate">
                {usuario?.rol === "ADMIN" ? "Administrador" : "Operador"}
              </p>
            </div>
            <button
              onClick={() => navigate("/cambiar-password")}
              title="Cambiar contraseña"
              className="text-slate-400 hover:text-brand-700 transition-colors"
            >
              <KeyRound size={18} />
            </button>
            <button
              onClick={logout}
              title="Cerrar sesión"
              className="text-slate-400 hover:text-red-600 transition-colors"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      {/* Contenido */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-slate-200 bg-white flex items-center justify-between px-8">
          <p className="text-sm text-slate-500">
            Workspace <span className="mx-1">/</span>{" "}
            <span className="text-slate-800 font-medium">Panel</span>
          </p>
          <div className="flex items-center gap-4">
            <NotificacionesDropdown />
            <span className="text-sm text-slate-500 capitalize">{hoy}</span>
          </div>
        </header>

        <main className="flex-1 p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
