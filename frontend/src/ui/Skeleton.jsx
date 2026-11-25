import './Skeleton.css'

/** Bloque gris mientras carga algo. Es decorativo: lo que carga se anuncia con aria-busy en el contenedor. */
export default function Skeleton({ alto = '1rem', ancho = '100%', className = '' }) {
  return (
    <span
      className={`ui-skeleton ${className}`.trim()}
      style={{ height: alto, width: ancho }}
      aria-hidden="true"
    />
  )
}
