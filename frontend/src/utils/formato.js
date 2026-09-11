/**
 * Arma el nombre a mostrar para una persona. AcademicOK devuelve el
 * nombre completo en un solo campo, así que `apellidos` puede venir
 * vacío — en ese caso se muestra solo `nombres`.
 */
export function nombreCompleto(persona) {
  if (!persona) return "—";
  const partes = [persona.nombres, persona.apellidos].filter(Boolean);
  return partes.join(" ") || "—";
}
