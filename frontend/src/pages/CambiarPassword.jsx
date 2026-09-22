import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { KeyRound, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

// Misma pantalla para los dos casos: el paso obligatorio del primer
// ingreso (usuario.debe_cambiar_password === true, ver RutaProtegida) y
// un cambio de contraseña voluntario más adelante desde el menú del
// panel (DashboardLayout) -- la única diferencia es si se puede
// cancelar y volver atrás.
export default function CambiarPassword() {
  const { usuario, cambiarPassword } = useAuth();
  const navigate = useNavigate();
  const obligatorio = Boolean(usuario?.debe_cambiar_password);

  const [passwordActual, setPasswordActual] = useState("");
  const [passwordNueva, setPasswordNueva] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (passwordNueva.length < 8) {
      setError("La contraseña nueva debe tener al menos 8 caracteres.");
      return;
    }
    if (passwordNueva !== confirmacion) {
      setError("La confirmación no coincide con la contraseña nueva.");
      return;
    }
    if (passwordNueva === passwordActual) {
      setError("La contraseña nueva debe ser distinta de la actual.");
      return;
    }

    setCargando(true);
    try {
      await cambiarPassword(passwordActual, passwordNueva);
      navigate("/", { replace: true });
    } catch (err) {
      setError(
        err?.response?.data?.detail || "No se pudo cambiar la contraseña. Intenta de nuevo."
      );
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F7F8F8] px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-brand flex items-center justify-center mb-3">
            <KeyRound className="text-white" size={26} />
          </div>
          <h1 className="text-xl font-bold text-slate-900">
            {obligatorio ? "Elegí tu contraseña" : "Cambiar contraseña"}
          </h1>
          <p className="text-sm text-slate-500 text-center mt-1">
            {obligatorio
              ? "Es la primera vez que entrás (o te resetearon la contraseña) -- elegí una propia antes de continuar."
              : "Ingresá tu contraseña actual y la nueva."}
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Contraseña actual
            </label>
            <input
              type="password"
              value={passwordActual}
              onChange={(e) => setPasswordActual(e.target.value)}
              required
              autoFocus
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
              placeholder="••••••••"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Contraseña nueva
            </label>
            <input
              type="password"
              value={passwordNueva}
              onChange={(e) => setPasswordNueva(e.target.value)}
              required
              minLength={8}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
              placeholder="Al menos 8 caracteres"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Confirmar contraseña nueva
            </label>
            <input
              type="password"
              value={confirmacion}
              onChange={(e) => setConfirmacion(e.target.value)}
              required
              minLength={8}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
              placeholder="Repetí la contraseña nueva"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={cargando}
            className="w-full bg-brand hover:bg-brand-600 disabled:opacity-60 text-white font-medium rounded-lg py-2.5 text-sm transition-colors"
          >
            {cargando ? "Guardando..." : "Guardar contraseña"}
          </button>

          {!obligatorio && (
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="w-full text-slate-500 hover:text-slate-700 text-sm py-1 transition-colors"
            >
              Cancelar
            </button>
          )}
        </form>

        {obligatorio && (
          <p className="flex items-center gap-1.5 justify-center text-xs text-slate-400 mt-4">
            <ShieldCheck size={14} />
            Este paso es obligatorio solo la primera vez.
          </p>
        )}
      </div>
    </div>
  );
}
