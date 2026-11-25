// Fechas del calendario. Se trabaja con textos "AAAA-MM-DD" (los que usa la API): comparan bien
// como texto y evitan los corrimientos de zona horaria de `new Date("2026-12-10")`.

export const NOMBRES_MESES = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];

export const INICIALES_DIAS = ["L", "M", "M", "J", "V", "S", "D"]; // la semana empieza el lunes

export function aISO(fecha) {
  const anio = fecha.getFullYear();
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  const dia = String(fecha.getDate()).padStart(2, "0");
  return `${anio}-${mes}-${dia}`;
}

// Semanas (filas de 7 días, de lunes a domingo) que hay que dibujar para mostrar un mes entero.
// `mes` va de 0 (enero) a 11. Los días de los meses vecinos completan la primera y la última semana.
export function semanasDelMes(anio, mes) {
  const primero = new Date(anio, mes, 1);
  const diasDesdeElLunes = (primero.getDay() + 6) % 7;
  const ultimo = new Date(anio, mes + 1, 0);
  const cursor = new Date(anio, mes, 1 - diasDesdeElLunes);

  const semanas = [];
  do {
    const semana = [];
    for (let i = 0; i < 7; i++) {
      semana.push({
        iso: aISO(cursor),
        numero: cursor.getDate(),
        delMes: cursor.getMonth() === mes,
        finDeSemana: i >= 5,
      });
      cursor.setDate(cursor.getDate() + 1);
    }
    semanas.push(semana);
  } while (cursor <= ultimo);
  return semanas;
}

export function mesSiguiente({ anio, mes }, pasos) {
  const fecha = new Date(anio, mes + pasos, 1);
  return { anio: fecha.getFullYear(), mes: fecha.getMonth() };
}

// Un trabajo ocupa los días en que se trabaja (`dias`, que pueden no ser seguidos). Si el dato no trae
// la lista, se toma todo el tramo desde su inicio hasta su fin, ambos inclusive.
export const cubreElDia = (trabajo, iso) =>
  trabajo.dias
    ? trabajo.dias.includes(iso)
    : Boolean(trabajo.fecha_inicio) && trabajo.fecha_inicio <= iso && iso <= trabajo.fecha_fin;

// Suma (o resta) días a una fecha "AAAA-MM-DD" sin pasar por zonas horarias.
export function sumarDias(iso, dias) {
  const [anio, mes, dia] = iso.split('-').map(Number)
  return aISO(new Date(anio, mes - 1, dia + dias))
}

// Los 7 días (lunes a domingo) de la semana que contiene a `iso`, con la misma forma que `semanasDelMes`.
export function semanaDe(iso) {
  const [anio, mes, dia] = iso.split('-').map(Number)
  const desdeElLunes = (new Date(anio, mes - 1, dia).getDay() + 6) % 7
  return Array.from({ length: 7 }, (_, i) => {
    const f = new Date(anio, mes - 1, dia - desdeElLunes + i)
    return { iso: aISO(f), numero: f.getDate(), delMes: true, finDeSemana: i >= 5 }
  })
}

const DIAS_LARGOS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado']

// "jueves 19 de noviembre" para una fecha "AAAA-MM-DD".
export function textoDelDia(iso) {
  const [anio, mes, dia] = iso.split('-').map(Number)
  return `${DIAS_LARGOS[new Date(anio, mes - 1, dia).getDay()]} ${dia} de ${NOMBRES_MESES[mes - 1]}`
}
