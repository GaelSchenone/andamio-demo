import './Avatar.css'

/** "Ana María Pérez" -> "AP". Para el círculo con iniciales del usuario. */
export function iniciales(nombre = '') {
  const partes = nombre.trim().split(/\s+/).filter(Boolean)
  if (partes.length === 0) return '?'
  const primera = partes[0][0]
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : ''
  return (primera + ultima).toUpperCase()
}

export default function Avatar({ nombre, tamano = 36 }) {
  return (
    <span
      className="ui-avatar"
      style={{ width: tamano, height: tamano, fontSize: tamano * 0.38 }}
      aria-hidden="true"
    >
      {iniciales(nombre)}
    </span>
  )
}
