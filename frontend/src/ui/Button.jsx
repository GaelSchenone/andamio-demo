import './Button.css'

/**
 * Botón. `variante`: primario (la cinta amarilla: UNA acción principal por pantalla), secundario,
 * fantasma o peligro. Con `cargando` queda desactivado y avisa a los lectores de pantalla.
 */
export default function Button({
  variante = 'secundario',
  tamano = 'md',
  icono: Icono,
  cargando = false,
  completo = false,
  type = 'button',
  className = '',
  children,
  disabled,
  ...resto
}) {
  const clases = ['ui-btn', `ui-btn--${variante}`, `ui-btn--${tamano}`, completo && 'ui-btn--completo', className]
    .filter(Boolean)
    .join(' ')
  return (
    <button
      type={type}
      className={clases}
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      {...resto}
    >
      {cargando ? <span className="ui-spinner" aria-hidden="true" /> : Icono && <Icono size={18} aria-hidden="true" />}
      {children}
    </button>
  )
}
