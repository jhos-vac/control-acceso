import React, { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowRightLeft, DoorOpen, LogIn, Users } from "lucide-react";
import api from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import StatCard from "../components/StatCard.jsx";
import { Cargando, ErrorMensaje } from "../components/EstadoCarga.jsx";
import {
  esMismoDia,
  etiquetaDiaCorto,
  formatHora,
  ultimosDias,
} from "../utils/fechas.js";
import { nombreCompleto } from "../utils/formato.js";

export default function Dashboard() {
  const { usuario } = useAuth();
  const [dentro, setDentro] = useState([]);
  const [personas, setPersonas] = useState([]);
  const [movimientos, setMovimientos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let activo = true;
    async function cargar() {
      setCargando(true);
      setError(null);
      try {
        const [resDentro, resPersonas, resMovimientos] = await Promise.all([
          api.get("/api/personas/dentro"),
          api.get("/api/personas"),
          api.get("/api/movimientos", { params: { limite: 500 } }),
        ]);
        if (!activo) return;
        setDentro(resDentro.data);
        setPersonas(resPersonas.data);
        setMovimientos(resMovimientos.data);
      } catch (err) {
        if (!activo) return;
        setError(err?.response?.data?.detail || err.message);
      } finally {
        if (activo) setCargando(false);
      }
    }
    cargar();
    return () => {
      activo = false;
    };
  }, []);

  const hoyMovs = useMemo(() => {
    const hoy = new Date();
    return movimientos.filter((m) => esMismoDia(new Date(m.fecha_hora), hoy));
  }, [movimientos]);

  const entradasHoy = hoyMovs.filter((m) => m.tipo === "ENTRADA").length;
  const salidasHoy = hoyMovs.filter((m) => m.tipo === "SALIDA").length;

  const datosGrafico = useMemo(() => {
    const dias = ultimosDias(7);
    return dias.map((dia) => {
      const delDia = movimientos.filter((m) => esMismoDia(new Date(m.fecha_hora), dia));
      return {
        dia: etiquetaDiaCorto(dia),
        Entradas: delDia.filter((m) => m.tipo === "ENTRADA").length,
        Salidas: delDia.filter((m) => m.tipo === "SALIDA").length,
      };
    });
  }, [movimientos]);

  const ultimosMovimientos = useMemo(
    () =>
      [...movimientos]
        .sort((a, b) => new Date(b.fecha_hora) - new Date(a.fecha_hora))
        .slice(0, 8),
    [movimientos]
  );

  const porcentajeDentro =
    personas.length > 0 ? Math.round((dentro.length / personas.length) * 100) : 0;

  if (cargando) return <Cargando mensaje="Cargando resumen..." />;
  if (error) return <ErrorMensaje mensaje={error} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Hola, {usuario?.nombre || usuario?.usuario}
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Este es el estado del edificio hoy.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          icon={Users}
          label="Presentes ahora"
          value={dentro.length}
          iconBg="bg-brand-50"
          iconColor="text-brand-600"
        />
        <StatCard
          icon={LogIn}
          label="Entradas hoy"
          value={entradasHoy}
          iconBg="bg-emerald-50"
          iconColor="text-emerald-600"
        />
        <StatCard
          icon={DoorOpen}
          label="Salidas hoy"
          value={salidasHoy}
          iconBg="bg-amber-50"
          iconColor="text-amber-600"
        />
        <StatCard
          icon={ArrowRightLeft}
          label="Total personas"
          value={personas.length}
          iconBg="bg-slate-100"
          iconColor="text-slate-600"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 bg-white border border-slate-200 rounded-2xl p-5">
          <h2 className="font-semibold text-slate-900 mb-1">Actividad de la semana</h2>
          <p className="text-sm text-slate-500 mb-4">Entradas y salidas por día</p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={datosGrafico} barGap={4}>
              <CartesianGrid vertical={false} stroke="#EEF1F2" />
              <XAxis
                dataKey="dia"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#94A3B8", fontSize: 12 }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#94A3B8", fontSize: 12 }}
                allowDecimals={false}
              />
              <Tooltip
                cursor={{ fill: "#F1F5F9" }}
                contentStyle={{ borderRadius: 12, borderColor: "#E2E8F0", fontSize: 13 }}
              />
              <Bar dataKey="Entradas" fill="#009EAD" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Salidas" fill="#99DFE3" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-brand text-white rounded-2xl p-5 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <span className="text-xs font-semibold tracking-wider uppercase text-brand-100">
              En tiempo real
            </span>
            <span className="flex items-center gap-1.5 text-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-white" />
              Activo
            </span>
          </div>
          <p className="text-5xl font-bold mb-1">{porcentajeDentro}%</p>
          <p className="text-sm text-brand-50/90 mb-6">
            del personal registrado está dentro
          </p>
          <div className="h-1.5 rounded-full bg-white/25 mb-2 overflow-hidden">
            <div
              className="h-full bg-white rounded-full"
              style={{ width: `${porcentajeDentro}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-brand-50/90">
            <span>{dentro.length} presentes</span>
            <span>{personas.length} total</span>
          </div>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl p-5">
        <h2 className="font-semibold text-slate-900 mb-4">Últimos movimientos</h2>
        {ultimosMovimientos.length === 0 ? (
          <p className="text-sm text-slate-500">Todavía no hay movimientos registrados.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-slate-100">
                  <th className="py-2 font-medium">Persona</th>
                  <th className="py-2 font-medium">Tipo</th>
                  <th className="py-2 font-medium">Hora</th>
                </tr>
              </thead>
              <tbody>
                {ultimosMovimientos.map((m) => (
                  <tr key={m.id} className="border-b border-slate-50 last:border-0">
                    <td className="py-2.5 text-slate-800">
                      {nombreCompleto(m.persona)}
                    </td>
                    <td className="py-2.5">
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
                    <td className="py-2.5 text-slate-500">{formatHora(m.fecha_hora)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
