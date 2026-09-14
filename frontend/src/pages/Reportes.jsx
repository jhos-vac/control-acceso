import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  CalendarDays,
  Download,
  DoorOpen,
  LogIn,
  LogOut,
  Users,
} from "lucide-react";
import api from "../api/client.js";
import { Cargando, ErrorMensaje } from "../components/EstadoCarga.jsx";
import StatCard from "../components/StatCard.jsx";
import { nombreCompleto } from "../utils/formato.js";
import {
  aFechaISO,
  formatFechaLarga,
  inicioDeMes,
  inicioDeSemana,
} from "../utils/fechas.js";

const TIPOS = [
  { id: "diario", label: "Diario" },
  { id: "semanal", label: "Semanal" },
  { id: "mensual", label: "Mensual" },
  { id: "personalizado", label: "Personalizado" },
];

function rangoParaTipo(tipo, fechaDiario) {
  const hoy = new Date();
  if (tipo === "diario") {
    const f = fechaDiario || aFechaISO(hoy);
    return { desde: f, hasta: f };
  }
  if (tipo === "semanal") {
    return { desde: aFechaISO(inicioDeSemana(hoy)), hasta: aFechaISO(hoy) };
  }
  if (tipo === "mensual") {
    return { desde: aFechaISO(inicioDeMes(hoy)), hasta: aFechaISO(hoy) };
  }
  return null; // personalizado: lo define el usuario
}

export default function Reportes() {
  const [searchParams] = useSearchParams();
  // Si se llega desde una notificación de la campana ("Ver reporte"), la
  // URL trae ?desde=...&hasta=..., y se abre directo en personalizado con
  // ese rango, generando el reporte automáticamente.
  const desdeUrl = searchParams.get("desde");
  const hastaUrl = searchParams.get("hasta");
  const vieneDeNotificacion = Boolean(desdeUrl && hastaUrl);

  const [tipo, setTipo] = useState(vieneDeNotificacion ? "personalizado" : "diario");
  const [fechaDiario, setFechaDiario] = useState(aFechaISO(new Date()));
  const [desdePersonalizado, setDesdePersonalizado] = useState(
    desdeUrl || aFechaISO(new Date())
  );
  const [hastaPersonalizado, setHastaPersonalizado] = useState(
    hastaUrl || aFechaISO(new Date())
  );

  const [puntos, setPuntos] = useState([]);
  const [puntoAccesoId, setPuntoAccesoId] = useState("");

  const [reporte, setReporte] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [descargando, setDescargando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .get("/api/puntos-acceso")
      .then(({ data }) => setPuntos(data))
      .catch(() => {
        /* si falla, simplemente no se filtra por punto de acceso */
      });
  }, []);

  const rango = useMemo(() => {
    if (tipo === "personalizado") {
      if (!desdePersonalizado || !hastaPersonalizado) return null;
      return { desde: desdePersonalizado, hasta: hastaPersonalizado };
    }
    return rangoParaTipo(tipo, fechaDiario);
  }, [tipo, fechaDiario, desdePersonalizado, hastaPersonalizado]);

  function paramsActuales() {
    return {
      desde: rango.desde,
      hasta: rango.hasta,
      ...(puntoAccesoId ? { punto_acceso_id: puntoAccesoId } : {}),
    };
  }

  async function generar() {
    if (!rango) return;
    if (rango.desde > rango.hasta) {
      setError('La fecha "desde" no puede ser posterior a la fecha "hasta".');
      return;
    }
    setCargando(true);
    setError(null);
    setReporte(null);
    try {
      const { data } = await api.get("/api/reportes/resumen", { params: paramsActuales() });
      setReporte(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "No se pudo generar el reporte.");
    } finally {
      setCargando(false);
    }
  }

  // Autogenerar cuando se llega desde el enlace "Ver reporte" de una
  // notificación (una sola vez, al montar).
  useEffect(() => {
    if (vieneDeNotificacion) {
      generar();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function descargarPdf() {
    if (!rango) return;
    setDescargando(true);
    setError(null);
    try {
      const respuesta = await api.get("/api/reportes/pdf", {
        params: { ...paramsActuales(), tipo },
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([respuesta.data], { type: "application/pdf" }));
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = `reporte_${tipo}_${rango.desde}_${rango.hasta}.pdf`;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError("No se pudo descargar el PDF.");
    } finally {
      setDescargando(false);
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Reportes</h1>
        <p className="text-sm text-slate-500 mt-1">
          Entradas, salidas e incidencias por período.
        </p>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4">
        {/* Selector de tipo de reporte */}
        <div className="flex flex-wrap gap-2">
          {TIPOS.map((t) => (
            <button
              key={t.id}
              onClick={() => {
                setTipo(t.id);
                setReporte(null);
                setError(null);
              }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                tipo === t.id
                  ? "bg-brand text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Controles según el tipo */}
        <div className="flex flex-wrap items-end gap-3">
          {tipo === "diario" && (
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Fecha</label>
              <input
                type="date"
                value={fechaDiario}
                onChange={(e) => setFechaDiario(e.target.value)}
                className="rounded-lg border border-slate-300 text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
              />
            </div>
          )}

          {(tipo === "semanal" || tipo === "mensual") && rango && (
            <div className="flex items-center gap-2 text-sm text-slate-600 bg-slate-50 rounded-lg px-3 py-2">
              <CalendarDays size={16} className="text-slate-400" />
              {formatFechaLarga(rango.desde)} — {formatFechaLarga(rango.hasta)}
              <span className="text-slate-400">
                ({tipo === "semanal" ? "semana actual, lunes a hoy" : "mes actual, día 1 a hoy"})
              </span>
            </div>
          )}

          {tipo === "personalizado" && (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Desde</label>
                <input
                  type="date"
                  value={desdePersonalizado}
                  onChange={(e) => setDesdePersonalizado(e.target.value)}
                  className="rounded-lg border border-slate-300 text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Hasta</label>
                <input
                  type="date"
                  value={hastaPersonalizado}
                  onChange={(e) => setHastaPersonalizado(e.target.value)}
                  className="rounded-lg border border-slate-300 text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Punto de acceso
            </label>
            <select
              value={puntoAccesoId}
              onChange={(e) => setPuntoAccesoId(e.target.value)}
              className="rounded-lg border border-slate-300 text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
            >
              <option value="">Todos</option>
              {puntos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={generar}
            disabled={cargando || !rango}
            className="bg-brand hover:bg-brand-600 disabled:opacity-60 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
          >
            {cargando ? "Generando..." : "Generar reporte"}
          </button>

          {reporte && (
            <button
              onClick={descargarPdf}
              disabled={descargando}
              className="flex items-center gap-2 border border-slate-300 hover:bg-slate-50 disabled:opacity-60 text-slate-700 text-sm font-medium rounded-lg px-4 py-2 transition-colors"
            >
              <Download size={16} />
              {descargando ? "Descargando..." : "Descargar PDF"}
            </button>
          )}
        </div>

        {error && <ErrorMensaje mensaje={error} />}
      </div>

      {cargando && <Cargando mensaje="Calculando el reporte..." />}

      {reporte && !cargando && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <StatCard
              icon={LogIn}
              label="Entradas registradas"
              value={reporte.total_entradas}
              iconBg="bg-emerald-50"
              iconColor="text-emerald-600"
            />
            <StatCard
              icon={LogOut}
              label="Salidas registradas"
              value={reporte.total_salidas}
              iconBg="bg-amber-50"
              iconColor="text-amber-600"
            />
            <StatCard
              icon={Users}
              label="Personas distintas que ingresaron"
              value={reporte.personas_entraron}
            />
            <StatCard
              icon={AlertTriangle}
              label="Incidencias (sin salida registrada)"
              value={reporte.incidencias.length}
              iconBg={reporte.incidencias.length ? "bg-red-50" : "bg-brand-50"}
              iconColor={reporte.incidencias.length ? "text-red-600" : "text-brand-600"}
            />
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100">
              <h3 className="font-semibold text-slate-900 text-sm">
                Entradas y salidas por día
              </h3>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-500">
                  <th className="py-2.5 px-5 font-medium">Fecha</th>
                  <th className="py-2.5 px-5 font-medium">Entradas</th>
                  <th className="py-2.5 px-5 font-medium">Salidas</th>
                </tr>
              </thead>
              <tbody>
                {reporte.por_dia.map((d) => (
                  <tr key={d.fecha} className="border-t border-slate-100">
                    <td className="py-2.5 px-5 text-slate-800">{formatFechaLarga(d.fecha)}</td>
                    <td className="py-2.5 px-5 text-slate-600">{d.entradas}</td>
                    <td className="py-2.5 px-5 text-slate-600">{d.salidas}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2">
              <AlertTriangle size={16} className="text-red-500" />
              <h3 className="font-semibold text-slate-900 text-sm">
                Incidencias — entrada sin salida registrada ese día
              </h3>
            </div>
            {reporte.incidencias.length === 0 ? (
              <p className="text-sm text-slate-500 px-5 py-6">
                No se encontraron incidencias en este período.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-red-50">
                  <tr className="text-left text-red-700">
                    <th className="py-2.5 px-5 font-medium">Fecha</th>
                    <th className="py-2.5 px-5 font-medium">Persona</th>
                    <th className="py-2.5 px-5 font-medium">Cédula</th>
                    <th className="py-2.5 px-5 font-medium">Hora de entrada</th>
                    <th className="py-2.5 px-5 font-medium">Punto de acceso</th>
                  </tr>
                </thead>
                <tbody>
                  {reporte.incidencias.map((m) => (
                    <tr key={m.id} className="border-t border-red-100">
                      <td className="py-2.5 px-5 text-slate-800">
                        {new Date(m.fecha_hora).toLocaleDateString("es-EC")}
                      </td>
                      <td className="py-2.5 px-5 text-slate-800">{nombreCompleto(m.persona)}</td>
                      <td className="py-2.5 px-5 text-slate-500">{m.persona?.cedula || "—"}</td>
                      <td className="py-2.5 px-5 text-slate-500">
                        {new Date(m.fecha_hora).toLocaleTimeString("es-EC", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                      <td className="py-2.5 px-5 text-slate-500 flex items-center gap-1.5">
                        <DoorOpen size={14} className="text-slate-400" />#{m.punto_acceso_id}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {reporte.actualmente_dentro.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-100">
                <h3 className="font-semibold text-slate-900 text-sm">
                  Personas dentro del edificio al momento de este reporte
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Entraron hoy y todavía no registran salida — no se cuenta como incidencia
                  mientras el día no haya terminado.
                </p>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr className="text-left text-slate-500">
                    <th className="py-2.5 px-5 font-medium">Persona</th>
                    <th className="py-2.5 px-5 font-medium">Cédula</th>
                    <th className="py-2.5 px-5 font-medium">Hora de entrada</th>
                  </tr>
                </thead>
                <tbody>
                  {reporte.actualmente_dentro.map((m) => (
                    <tr key={m.id} className="border-t border-slate-100">
                      <td className="py-2.5 px-5 text-slate-800">{nombreCompleto(m.persona)}</td>
                      <td className="py-2.5 px-5 text-slate-500">{m.persona?.cedula || "—"}</td>
                      <td className="py-2.5 px-5 text-slate-500">
                        {new Date(m.fecha_hora).toLocaleTimeString("es-EC", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
