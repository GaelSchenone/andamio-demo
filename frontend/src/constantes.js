// Textos y valores compartidos por varias pantallas (antes estaban repetidos en cada componente).
import { formatoFecha, formatoMoneda } from './formato'

export const TIPOS_CLIENTE = { casa: 'Casa', consorcio: 'Consorcio' }
export const ROLES = { dueno: 'Dueño', empleado: 'Empleado' }
export const CAUSAS = { clima: 'El clima', cliente: 'El cliente', materiales: 'Materiales', otra: 'Otra' }
export const CONCEPTOS_COBRO = { sena: 'Seña', saldo: 'Saldo' }
export const LARGO_MINIMO_PASSWORD = 10 // el mismo mínimo que valida el backend (passwords.LARGO_MINIMO)

const sinCentavos = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 })

// "$ 1.450.000" si es redondo y "$ 1.450.000,50" si tiene centavos: los ceros de más ensucian y ocupan lugar.
export const pesos = (n) => (Number.isInteger(Number(n)) ? `$ ${sinCentavos.format(Number(n))}` : `$ ${formatoMoneda(n)}`)
export const formatoCantidad = (n) => String(n).replace('.', ',')

const diasDelTramo = (t) => Math.round((new Date(t.fecha_fin) - new Date(t.fecha_inicio)) / 86_400_000) + 1

export function textoDeFechas(t) {
  if (!t.fecha_inicio) return 'Sin fecha todavía'
  if (t.fecha_inicio === t.fecha_fin) return `El ${formatoFecha(t.fecha_inicio)}`
  // Días sueltos (no seguidos): se dice cuántos son y entre qué fechas caen.
  if (t.dias?.length && t.dias.length < diasDelTramo(t)) {
    return `${t.dias.length} días entre el ${formatoFecha(t.fecha_inicio)} y el ${formatoFecha(t.fecha_fin)}`
  }
  return `Del ${formatoFecha(t.fecha_inicio)} al ${formatoFecha(t.fecha_fin)}`
}
