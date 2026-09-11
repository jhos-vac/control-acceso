const DIAS_CORTOS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];

export function esMismoDia(fechaA, fechaB) {
  return (
    fechaA.getFullYear() === fechaB.getFullYear() &&
    fechaA.getMonth() === fechaB.getMonth() &&
    fechaA.getDate() === fechaB.getDate()
  );
}

/** Devuelve un arreglo de los últimos `n` días (más antiguo primero). */
export function ultimosDias(n = 7) {
  const dias = [];
  const hoy = new Date();
  for (let i = n - 1; i >= 0; i -= 1) {
    const d = new Date(hoy);
    d.setDate(hoy.getDate() - i);
    dias.push(d);
  }
  return dias;
}

export function etiquetaDiaCorto(fecha) {
  const capital = DIAS_CORTOS[fecha.getDay()];
  return capital.charAt(0).toUpperCase() + capital.slice(1);
}

export function formatHora(fechaISO) {
  return new Date(fechaISO).toLocaleTimeString("es-EC", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatFechaHora(fechaISO) {
  return new Date(fechaISO).toLocaleString("es-EC", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
