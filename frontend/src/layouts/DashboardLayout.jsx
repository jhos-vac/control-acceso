import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  Bell,
  Calendar,
  DoorOpen,
  LayoutGrid,
  LogOut,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

const navItems = [
  { to: "/", label: "Resumen", icon: LayoutGrid, end: true },
  { to: "/registros", label: "Registros", icon: Calendar },
  { to: "/personas", label: "Personas", icon: Users },
  { to: "/puntos-acceso", label: "Puntos de acceso", icon: DoorOpen },
];

const hoy = new Date().toLocaleDateString("es-EC", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

export default function DashboardLayout() {
  const { usuario, logout } = useAuth();

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
            <button className="relative text-slate-400 hover:text-slate-600">
              <Bell size={19} />
              <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-brand" />
            </button>
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
