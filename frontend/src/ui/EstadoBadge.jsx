import {
  Ban,
  BadgeDollarSign,
  CalendarCheck,
  CalendarClock,
  CircleCheck,
  CircleX,
  FilePenLine,
  HardHat,
  Send,
} from 'lucide-react'
import { ESTADOS_PRESUPUESTO, ESTADOS_TRABAJO } from '../estados'
import Badge from './Badge'

// Cada estado = ícono + texto + color. El color solo refuerza; el ícono y el texto bastan.
const DE_TRABAJO = {
  por_agendar: { tono: 'alerta', icono: CalendarClock },
  agendado: { tono: 'info', icono: CalendarCheck },
  en_curso: { tono: 'ok', icono: HardHat },
  terminado: { tono: 'neutro', icono: CircleCheck },
  cobrado: { tono: 'ok', icono: BadgeDollarSign },
  cancelado: { tono: 'neutro', icono: Ban },
}

const DE_PRESUPUESTO = {
  borrador: { tono: 'neutro', icono: FilePenLine },
  enviado: { tono: 'info', icono: Send },
  aprobado: { tono: 'ok', icono: CircleCheck },
  rechazado: { tono: 'peligro', icono: CircleX },
}

/** Estado de un trabajo (`tipo="trabajo"`) o de un presupuesto (`tipo="presupuesto"`). */
export default function EstadoBadge({ tipo = 'trabajo', estado }) {
  const esTrabajo = tipo === 'trabajo'
  const { tono, icono } = (esTrabajo ? DE_TRABAJO : DE_PRESUPUESTO)[estado] ?? { tono: 'neutro' }
  const etiqueta = (esTrabajo ? ESTADOS_TRABAJO : ESTADOS_PRESUPUESTO)[estado] ?? estado
  return (
    <Badge tono={tono} icono={icono}>
      {etiqueta}
    </Badge>
  )
}
