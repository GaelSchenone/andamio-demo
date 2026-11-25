import { Search, X } from 'lucide-react'
import './SearchField.css'

/** Buscador con ícono y botón de limpiar. `etiqueta` es el nombre accesible (no se ve, pero se anuncia). */
export default function SearchField({ etiqueta, valor, onChange, placeholder, className = '', ...resto }) {
  return (
    <div className={`ui-buscador ${className}`.trim()} role="search">
      <Search size={18} aria-hidden="true" className="ui-buscador-lupa" />
      <input
        type="search"
        aria-label={etiqueta}
        placeholder={placeholder}
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        {...resto}
      />
      {valor && (
        <button
          type="button"
          className="ui-buscador-limpiar"
          aria-label="Limpiar búsqueda"
          onClick={() => onChange('')}
        >
          <X size={16} aria-hidden="true" />
        </button>
      )}
    </div>
  )
}
