import './IconButton.css'

/** Botón que es solo un ícono: la etiqueta (`etiqueta`) es obligatoria para lectores de pantalla y tooltip. */
export default function IconButton({ icono: Icono, etiqueta, tamano = 20, className = '', ...resto }) {
  return (
    <button
      type="button"
      className={`ui-icon-btn ${className}`.trim()}
      aria-label={etiqueta}
      title={etiqueta}
      {...resto}
    >
      <Icono size={tamano} aria-hidden="true" />
    </button>
  )
}
