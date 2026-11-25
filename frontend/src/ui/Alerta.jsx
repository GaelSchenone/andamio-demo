import { CircleAlert, CircleCheck, Info } from 'lucide-react'
import './Alerta.css'

const ICONOS = { peligro: CircleAlert, ok: CircleCheck, info: Info }

/** Mensaje en línea dentro de una pantalla o un formulario (ícono + texto, nunca solo color). */
export default function Alerta({ tono = 'peligro', children, className = '' }) {
  const Icono = ICONOS[tono]
  return (
    <div className={`ui-alerta ui-alerta--${tono} ${className}`.trim()} role={tono === 'peligro' ? 'alert' : 'status'}>
      <Icono size={18} aria-hidden="true" />
      <p>{children}</p>
    </div>
  )
}
