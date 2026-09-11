import React, { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import api from "../api/client.js";
import { Cargando, ErrorMensaje } from "../components/EstadoCarga.jsx";
import { formatFechaHora } from "../utils/fechas.js";
import { nombreCompleto } from "../utils/formato.js";

export default function Registros() {
  const [movimientos, setMovimientos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [busqueda, setBusqueda] = useState("");
  const [filtroTipo, setFiltroTipo] = useState("TODOS");

  useEffect(() => {
    let activo = true;
    async function cargar() {
      setCargando(true);
      setError(null);
      try {
        const { data } = await api.get("/api/movimientos", { params: { limite: 300 } });
        if (activo) setMovimientos(data);
      } catch (err) {
        if (activo) setError(err?.response?.data?.detail || err.message);
      } finally {
        if (activo) setCargando(false);
      }
    }
    cargar();
    return () => {
      activo = false;
    };
  }, []);

  const filtrados = useMemo(() => {
    const texto = busqueda.trim().toLowerCase();
    return movimientos
      .filter((m) => filtroTipo === "TODOS" || m.tipo === filtroTipo)
      .filter((m) => {
        if (!texto) return true;
        const nombre = m.persona
          ? `${nombreCompleto(m.persona)} ${m.persona.cedula}`.toLowerCase()
          : "";
        return nombre.includes(texto);
      })
      .sort((a, b) => new Date(b.fecha_hora) - new Date(a.fecha_hora));
  }, [movimientos, busqueda, filtroTipo]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Registros</h1>
        <p className="text-sm text-slate-500 mt-1">Historial de entradas y salidas.</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <input
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar por nombre o cédula..."
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
          />
        </div>
        <select
          value={filtroTipo}
          onChange={(e) => setFiltroTipo(e.target.value)}
          className="rounded-lg border border-slate-300 text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
        >
          <option value="TODOS">Todos</option>
          <option value="ENTRADA">Entradas</option>
          <option value="SALIDA">Salidas</option>
        </select>
      </div>

      {cargando ? (
        <Cargando mensaje="Cargando registros..." />
      ) : error ? (
        <ErrorMensaje mensaje={error} />
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr className="text-left text-slate-500">
                <th className="py-3 px-5 font-medium">Persona</th>
                <th className="py-3 px-5 font-medium">Cédula</th>
                <th className="py-3 px-5 font-medium">Tipo</th>
                <th className="py-3 px-5 font-medium">Fecha y hora</th>
                <th className="py-3 px-5 font-medium">Punto de acceso</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    No hay registros que coincidan con el filtro.
                  </td>
                </tr>
              ) : (
                filtrados.map((m) => (
                  <tr key={m.id} className="border-t border-slate-100">
                    <td className="py-3 px-5 text-slate-800">
                      {nombreCompleto(m.persona)}
                    </td>
                    <td className="py-3 px-5 text-slate-500">
                      {m.persona?.cedula || "—"}
                    </td>
                    <td className="py-3 px-5">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                          m.tipo === "ENTRADA"
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-amber-50 text-amber-700"
                        }`}
                      >
                        {m.tipo}
                      </span>
                    </td>
                    <td className="py-3 px-5 text-slate-500">
                      {formatFechaHora(m.fecha_hora)}
                    </td>
                    <td className="py-3 px-5 text-slate-500">
                      #{m.punto_acceso_id}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
