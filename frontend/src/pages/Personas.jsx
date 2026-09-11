import React, { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import api from "../api/client.js";
import { Cargando, ErrorMensaje } from "../components/EstadoCarga.jsx";
import { nombreCompleto } from "../utils/formato.js";

export default function Personas() {
  const [personas, setPersonas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [busqueda, setBusqueda] = useState("");

  useEffect(() => {
    let activo = true;
    async function cargar() {
      setCargando(true);
      setError(null);
      try {
        const { data } = await api.get("/api/personas");
        if (activo) setPersonas(data);
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

  const filtradas = useMemo(() => {
    const texto = busqueda.trim().toLowerCase();
    if (!texto) return personas;
    return personas.filter((p) =>
      `${nombreCompleto(p)} ${p.cedula} ${p.correo || ""}`.toLowerCase().includes(texto)
    );
  }, [personas, busqueda]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Personas</h1>
        <p className="text-sm text-slate-500 mt-1">
          Personal registrado en el sistema ({personas.length}).
        </p>
      </div>

      <div className="relative max-w-sm">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Buscar por nombre, cédula o correo..."
          className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
        />
      </div>

      {cargando ? (
        <Cargando mensaje="Cargando personas..." />
      ) : error ? (
        <ErrorMensaje mensaje={error} />
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr className="text-left text-slate-500">
                <th className="py-3 px-5 font-medium">Nombre</th>
                <th className="py-3 px-5 font-medium">Cédula</th>
                <th className="py-3 px-5 font-medium">Correo</th>
                <th className="py-3 px-5 font-medium">idperfil</th>
                <th className="py-3 px-5 font-medium">Estado</th>
              </tr>
            </thead>
            <tbody>
              {filtradas.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    No hay personas registradas todavía.
                  </td>
                </tr>
              ) : (
                filtradas.map((p) => (
                  <tr key={p.id} className="border-t border-slate-100">
                    <td className="py-3 px-5 text-slate-800">{nombreCompleto(p)}</td>
                    <td className="py-3 px-5 text-slate-500">{p.cedula}</td>
                    <td className="py-3 px-5 text-slate-500">{p.correo || "—"}</td>
                    <td className="py-3 px-5 text-slate-500">{p.idperfil || "—"}</td>
                    <td className="py-3 px-5">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                          p.estado === "ACTIVO"
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {p.estado}
                      </span>
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
