import './Marca.css'

/**
 * Logo de Obras Demo (un andamio esquemático). Es el SVG recortado como máscara y pintado con el color del texto, así se ve
 * en el tema claro (negro) y en el oscuro (claro) sin tener dos archivos. Las dos variantes usan el mismo
 * dibujo; `completa` es la que se usa en el login.
 */
export default function Marca({ variante = 'completa', ancho = 96, className = '' }) {
  return (
    <span
      role="img"
      aria-label="Obras Demo"
      className={`marca marca--${variante} ${className}`.trim()}
      style={{ width: ancho }}
    />
  )
}
