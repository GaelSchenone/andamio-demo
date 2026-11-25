import './Badge.css'

/**
 * Etiqueta de estado. Nunca comunica solo con color (color.md › Inclusive color): lleva siempre
 * texto, y un ícono cuando representa un estado.
 */
export default function Badge({ tono = 'neutro', icono: Icono, children, className = '' }) {
  return (
    <span className={`ui-badge ui-badge--${tono} ${className}`.trim()}>
      {Icono && <Icono size={14} aria-hidden="true" />}
      {children}
    </span>
  )
}
