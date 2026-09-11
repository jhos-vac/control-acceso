import React from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

export function Cargando({ mensaje = "Cargando..." }) {
  return (
    <div className="flex items-center gap-2 text-slate-500 text-sm py-10 justify-center">
      <Loader2 size={16} className="animate-spin" />
      {mensaje}
    </div>
  );
}

export function ErrorMensaje({ mensaje }) {
  return (
    <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-3 text-sm">
      <AlertTriangle size={16} />
      {mensaje ||
        "No se pudo conectar con el backend. Verifica que la API esté corriendo."}
    </div>
  );
}
