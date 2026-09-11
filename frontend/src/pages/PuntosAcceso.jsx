import React, { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import api from "../api/client.js";
import { Cargando, ErrorMensaje } from "../components/EstadoCarga.jsx";

export default function PuntosAcceso() {
  const [puntos, setPuntos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [nombre, setNombre] = useState("");
  const [ubicacion, setUbicacion] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [errorForm, setErrorForm] = useState(null);

  async function cargar() {
    setCargando(true);
    setError(null);
    try {
      const { data } = await api.get("/api/puntos-acceso");
      setPuntos(data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    cargar();
  }, []);

  async function handleCrear(e) {
    e.preventDefault();
    setGuardando(true);
    setErrorForm(null);
    try {
      await api.post("/api/puntos-acceso", { nombre, ubicacion, estado: true });
      setNombre("");
      setUbicacion("");
      setMostrarForm(false);
      await cargar();
    } catch (err) {
      setErrorForm(err?.response?.data?.detail || "No se pudo crear el punto de acceso.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Puntos de acceso</h1>
          <p className="text-sm text-slate-500 mt-1">
            Terminales y puertas registradas en el sistema.
          </p>
        </div>
        <button
          onClick={() => setMostrarForm((v) => !v)}
          className="flex items-center gap-2 bg-brand hover:bg-brand-600 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
        >
          <Plus size={16} />
          Nuevo punto
        </button>
      </div>

      {mostrarForm && (
        <form
          onSubmit={handleCrear}
          className="bg-white border border-slate-200 rounded-2xl p-5 flex flex-col sm:flex-row gap-3 items-start sm:items-end"
        >
          <div className="flex-1 w-full">
            <label className="block text-xs font-medium text-slate-600 mb-1">Nombre</label>
            <input
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              required
              placeholder="Ej. Entrada principal"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
            />
          </div>
          <div className="flex-1 w-full">
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Ubicación
            </label>
            <input
              value={ubicacion}
              onChange={(e) => setUbicacion(e.target.value)}
              placeholder="Ej. Puerta lateral, planta baja"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
            />
          </div>
          <button
            type="submit"
            disabled={guardando}
            className="bg-brand hover:bg-brand-600 disabled:opacity-60 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
          >
            {guardando ? "Guardando..." : "Guardar"}
          </button>
          {errorForm && <p className="text-sm text-red-600 w-full">{errorForm}</p>}
        </form>
      )}

      {cargando ? (
        <Cargando mensaje="Cargando puntos de acceso..." />
      ) : error ? (
        <ErrorMensaje mensaje={error} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {puntos.length === 0 ? (
            <p className="text-sm text-slate-500 col-span-full">
              No hay puntos de acceso registrados todavía.
            </p>
          ) : (
            puntos.map((p) => (
              <div
                key={p.id}
                className="bg-white border border-slate-200 rounded-2xl p-5"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-slate-900">{p.nombre}</h3>
                  <span
                    className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                      p.estado
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {p.estado ? "Activo" : "Inactivo"}
                  </span>
                </div>
                <p className="text-sm text-slate-500">{p.ubicacion || "Sin ubicación"}</p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
