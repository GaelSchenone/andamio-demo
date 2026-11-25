const formateadorMoneda = new Intl.NumberFormat("es-AR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatoMoneda(valor) {
  return formateadorMoneda.format(Number(valor) || 0);
}

export function formatoFecha(isoDate) {
  if (!isoDate) return "-";
  const [anio, mes, dia] = isoDate.split("-");
  return `${dia}/${mes}/${anio}`;
}

export function hoyISO() {
  const ahora = new Date();
  const offset = ahora.getTimezoneOffset();
  const local = new Date(ahora.getTime() - offset * 60_000);
  return local.toISOString().slice(0, 10);
}
