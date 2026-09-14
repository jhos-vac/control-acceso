import React, { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Pencil, Plus, Power, Zap } from "lucide-react";
import api from "../api/client.js";
import { Cargando, ErrorMensaje } from "../components/EstadoCarga.jsx";
import { useAuth } from "../context/AuthContext.jsx";

// Mismo intervalo que el latido del terminal (ver
// terminal/leer_qr.py -> INTERVALO_LATIDO), para que el estado "en
// línea" se vea razonablemente al día.
const INTERVALO_REFRESCO_MS = 15000;

function TarjetaPuntoAcceso({
  punto,
  esAdmin,
  destacado,
  apagando,
  encendiendo,
  onApagar,
  onEncender,
  onEditar,
  refCallback,
}) {
  return (
    <div
      ref={refCallback}
      className={`bg-white border rounded-2xl p-5 transition-shadow ${
        destacado
          ? "border-brand ring-2 ring-brand-200 shadow-md"
          : "border-slate-200"
      }`}
    >
      <div className="flex items-start justify-between mb-2 gap-2">
        <h3 className="font-semibold text-slate-900">{punto.nombre}</h3>
        <span
          className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
            punto.estado
              ? "bg-emerald-50 text-emerald-700"
              : "bg-slate-100 text-slate-600"
          }`}
        >
          {punto.estado ? "Activo" : "Inactivo"}
        </span>
      </div>
      <p className="text-sm text-slate-500 mb-1">{punto.ubicacion || "Sin ubicación"}</p>
      <p className="text-xs text-slate-400 mb-3">
        {punto.mac_address ? (
          <>MAC: {punto.mac_address}</>
        ) : (
          <span className="text-amber-600">Sin MAC configurada (no se puede encender a distancia)</span>
        )}
      </p>

      <div className="flex items-center justify-between pt-3 border-t border-slate-100">
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-600">
          <span
            className={`w-2 h-2 rounded-full ${
              punto.en_linea ? "bg-emerald-500" : "bg-slate-300"
            }`}
          />
          {punto.en_linea ? "En línea" : "Sin conexión"}
        </span>

        {esAdmin && (
          <div className="flex items-center gap-3">
            <button
              onClick={() => onEditar(punto)}
              title="Editar (nombre, ubicación, MAC)"
              className="flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-700"
            >
              <Pencil size={13} />
              Editar
            </button>

            {punto.en_linea ? (
              <button
                onClick={() => onApagar(punto)}
                disabled={apagando}
                title="Apagar este dispositivo"
                className="flex items-center gap-1.5 text-xs font-medium text-red-600 hover:text-red-700 disabled:text-slate-300 disabled:cursor-not-allowed"
              >
                <Power size={14} />
                {apagando ? "Enviando..." : "Apagar"}
              </button>
            ) : (
              <button
                onClick={() => onEncender(punto)}
                disabled={encendiendo || !punto.mac_address}
                title={
                  punto.mac_address
                    ? "Intentar encender por Wake-on-LAN (requiere que el equipo esté en la misma red y lo soporte)"
                    : "Agrega la dirección MAC editando este punto de acceso para poder encenderlo a distancia"
                }
                className="flex items-center gap-1.5 text-xs font-medium text-brand-700 hover:text-brand-800 disabled:text-slate-300 disabled:cursor-not-allowed"
              >
                <Zap size={14} />
                {encendiendo ? "Enviando..." : "Encender"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function FormularioPunto({ titulo, valores, onCambiar, onCancelar, onGuardar, guardando, error }) {
  return (
    <form
      onSubmit={onGuardar}
      className="bg-white border border-slate-200 rounded-2xl p-5 flex flex-col gap-3"
    >
      <p className="text-sm font-semibold text-slate-900">{titulo}</p>
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
        <div className="flex-1 w-full">
          <label className="block text-xs font-medium text-slate-600 mb-1">Nombre</label>
          <input
            value={valores.nombre}
            onChange={(e) => onCambiar({ ...valores, nombre: e.target.value })}
            required
            placeholder="Ej. Entrada principal"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
          />
        </div>
        <div className="flex-1 w-full">
          <label className="block text-xs font-medium text-slate-600 mb-1">Ubicación</label>
          <input
            value={valores.ubicacion}
            onChange={(e) => onCambiar({ ...valores, ubicacion: e.target.value })}
            placeholder="Ej. Puerta lateral, planta baja"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
          />
        </div>
      </div>
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
        <div className="flex-1 w-full">
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Dirección MAC (opcional — para poder encenderlo a distancia)
          </label>
          <input
            value={valores.mac_address}
            onChange={(e) => onCambiar({ ...valores, mac_address: e.target.value })}
            placeholder="AA:BB:CC:DD:EE:FF"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand font-mono"
          />
          <p className="text-xs text-slate-400 mt-1">
            Se encuentra en la configuración de red del equipo. Sin esto, el botón
            "Encender" no va a funcionar.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={guardando}
            className="bg-brand hover:bg-brand-600 disabled:opacity-60 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors whitespace-nowrap"
          >
            {guardando ? "Guardando..." : "Guardar"}
          </button>
          <button
            type="button"
            onClick={onCancelar}
            className="border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium rounded-lg px-4 py-2 transition-colors"
          >
            Cancelar
          </button>
        </div>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </form>
  );
}

const FORM_VACIO = { nombre: "", ubicacion: "", mac_address: "" };

export default function PuntosAcceso() {
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "ADMIN";
  const [searchParams] = useSearchParams();
  const destacarId = searchParams.get("destacar");
  const tarjetaDestacadaRef = useRef(null);

  const [puntos, setPuntos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const [mostrarForm, setMostrarForm] = useState(false);
  const [formNuevo, setFormNuevo] = useState(FORM_VACIO);
  const [guardando, setGuardando] = useState(false);
  const [errorForm, setErrorForm] = useState(null);

  const [editandoId, setEditandoId] = useState(null);
  const [formEditar, setFormEditar] = useState(FORM_VACIO);
  const [guardandoEdicion, setGuardandoEdicion] = useState(false);
  const [errorEdicion, setErrorEdicion] = useState(null);

  const [apagandoId, setApagandoId] = useState(null);
  const [encendiendoId, setEncendiendoId] = useState(null);
  const [avisoEncendido, setAvisoEncendido] = useState(null);

  async function cargar({ mostrarCarga = true } = {}) {
    if (mostrarCarga) setCargando(true);
    setError(null);
    try {
      const { data } = await api.get("/api/puntos-acceso");
      setPuntos(data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      if (mostrarCarga) setCargando(false);
    }
  }

  useEffect(() => {
    cargar();
    // Refresca en segundo plano (sin mostrar el spinner de carga) para
    // que el punto pase a "En línea"/"Sin conexión" sin recargar la página.
    const intervalo = setInterval(() => cargar({ mostrarCarga: false }), INTERVALO_REFRESCO_MS);
    return () => clearInterval(intervalo);
  }, []);

  // Si se llega desde la campana ("ir al dispositivo"), hace scroll hasta
  // la tarjeta correspondiente una vez que la lista ya cargó.
  useEffect(() => {
    if (destacarId && !cargando && tarjetaDestacadaRef.current) {
      tarjetaDestacadaRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [destacarId, cargando, puntos]);

  async function handleApagar(punto) {
    const confirmado = window.confirm(
      `¿Apagar "${punto.nombre}"?\n\n` +
        "El terminal recibirá la orden en los próximos segundos y se " +
        "apagará solo. Mientras esté apagado, no va a poder leer QR ni " +
        "registrar entradas/salidas en ese punto — hay que volver a " +
        "encenderlo (o usar el botón \"Encender\" si tiene MAC configurada).\n\n" +
        "Nota: si el terminal corre en una PC (como en las pruebas " +
        "actuales), esto apaga toda la PC, no solo el programa."
    );
    if (!confirmado) return;

    setApagandoId(punto.id);
    try {
      await api.post(`/api/puntos-acceso/${punto.id}/comando`, { comando: "APAGAR" });
      await cargar({ mostrarCarga: false });
    } catch (err) {
      alert(err?.response?.data?.detail || "No se pudo enviar la orden de apagado.");
    } finally {
      setApagandoId(null);
    }
  }

  async function handleEncender(punto) {
    setAvisoEncendido(null);
    setEncendiendoId(punto.id);
    try {
      await api.post(`/api/puntos-acceso/${punto.id}/encender`);
      setAvisoEncendido(
        `Se mandó la señal de encendido a "${punto.nombre}". Esto solo funciona si el ` +
          "equipo está en la misma red local, tiene Wake-on-LAN habilitado y está " +
          "conectado por cable — una Raspberry Pi apagada por lo general no soporta esto. " +
          "Puede tardar unos segundos en aparecer como \"En línea\"."
      );
      setTimeout(() => cargar({ mostrarCarga: false }), 5000);
    } catch (err) {
      alert(err?.response?.data?.detail || "No se pudo enviar la señal de encendido.");
    } finally {
      setEncendiendoId(null);
    }
  }

  async function handleCrear(e) {
    e.preventDefault();
    setGuardando(true);
    setErrorForm(null);
    try {
      await api.post("/api/puntos-acceso", { ...formNuevo, estado: true });
      setFormNuevo(FORM_VACIO);
      setMostrarForm(false);
      await cargar();
    } catch (err) {
      setErrorForm(err?.response?.data?.detail || "No se pudo crear el punto de acceso.");
    } finally {
      setGuardando(false);
    }
  }

  function abrirEdicion(punto) {
    setEditandoId(punto.id);
    setFormEditar({
      nombre: punto.nombre,
      ubicacion: punto.ubicacion || "",
      mac_address: punto.mac_address || "",
    });
    setErrorEdicion(null);
  }

  async function handleGuardarEdicion(e) {
    e.preventDefault();
    setGuardandoEdicion(true);
    setErrorEdicion(null);
    try {
      await api.patch(`/api/puntos-acceso/${editandoId}`, formEditar);
      setEditandoId(null);
      await cargar({ mostrarCarga: false });
    } catch (err) {
      setErrorEdicion(err?.response?.data?.detail || "No se pudo guardar el cambio.");
    } finally {
      setGuardandoEdicion(false);
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
        {esAdmin && (
          <button
            onClick={() => {
              setMostrarForm((v) => !v);
              setEditandoId(null);
            }}
            className="flex items-center gap-2 bg-brand hover:bg-brand-600 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
          >
            <Plus size={16} />
            Nuevo punto
          </button>
        )}
      </div>

      {avisoEncendido && (
        <div className="bg-brand-50 border border-brand-200 text-brand-800 text-sm rounded-xl px-4 py-3">
          {avisoEncendido}
        </div>
      )}

      {mostrarForm && (
        <FormularioPunto
          titulo="Nuevo punto de acceso"
          valores={formNuevo}
          onCambiar={setFormNuevo}
          onCancelar={() => setMostrarForm(false)}
          onGuardar={handleCrear}
          guardando={guardando}
          error={errorForm}
        />
      )}

      {editandoId && (
        <FormularioPunto
          titulo={`Editar "${puntos.find((p) => p.id === editandoId)?.nombre || ""}"`}
          valores={formEditar}
          onCambiar={setFormEditar}
          onCancelar={() => setEditandoId(null)}
          onGuardar={handleGuardarEdicion}
          guardando={guardandoEdicion}
          error={errorEdicion}
        />
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
              <TarjetaPuntoAcceso
                key={p.id}
                punto={p}
                esAdmin={esAdmin}
                destacado={String(p.id) === destacarId}
                apagando={apagandoId === p.id}
                encendiendo={encendiendoId === p.id}
                onApagar={handleApagar}
                onEncender={handleEncender}
                onEditar={abrirEdicion}
                refCallback={String(p.id) === destacarId ? tarjetaDestacadaRef : undefined}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
