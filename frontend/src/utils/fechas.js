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

/** "YYYY-MM-DD" en hora LOCAL (evita el corrimiento de día que da
 * toISOString(), que convierte a UTC primero). */
export function aFechaISO(fecha) {
  const y = fecha.getFullYear();
  const m = String(fecha.getMonth() + 1).padStart(2, "0");
  const d = String(fecha.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function formatFechaLarga(fechaISO) {
  // fechaISO viene como "YYYY-MM-DD" (sin hora) -> se arma en local para
  // no correr de día por interpretarlo como UTC medianoche.
  const [y, m, d] = fechaISO.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("es-EC", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Lunes de la semana de `fecha` (semana lunes-domingo). */
export function inicioDeSemana(fecha = new Date()) {
  const d = new Date(fecha);
  const diaSemana = d.getDay(); // 0=domingo, 1=lunes, ...
  const diferencia = diaSemana === 0 ? -6 : 1 - diaSemana;
  d.setDate(d.getDate() + diferencia);
  return d;
}

export function inicioDeMes(fecha = new Date()) {
  return new Date(fecha.getFullYear(), fecha.getMonth(), 1);
}
