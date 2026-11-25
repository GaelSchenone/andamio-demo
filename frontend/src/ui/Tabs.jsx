import './Tabs.css'

/**
 * Pestañas accesibles (role tablist/tab). Solo dibuja la fila de pestañas: el contenido lo muestra quien
 * la usa, con role="tabpanel" y aria-labelledby={`pestana-${id}`}. Flechas, Inicio y Fin cambian de
 * pestaña, y solo la activa entra en el orden de Tab (patrón WAI-ARIA).
 */
export default function Tabs({ pestanas, activa, onChange, etiqueta }) {
  function alTeclear(evento, indice) {
    const ultimo = pestanas.length - 1
    const destino = {
      ArrowRight: indice === ultimo ? 0 : indice + 1,
      ArrowLeft: indice === 0 ? ultimo : indice - 1,
      Home: 0,
      End: ultimo,
    }[evento.key]
    if (destino === undefined) return
    evento.preventDefault()
    onChange(pestanas[destino].id)
    document.getElementById(`pestana-${pestanas[destino].id}`)?.focus()
  }

  return (
    <div className="ui-tabs" role="tablist" aria-label={etiqueta}>
      {pestanas.map(({ id, etiqueta: texto }, indice) => (
        <button
          key={id}
          id={`pestana-${id}`}
          type="button"
          role="tab"
          aria-selected={activa === id}
          aria-controls={`panel-${id}`}
          tabIndex={activa === id ? 0 : -1}
          className={activa === id ? 'is-activa' : undefined}
          onClick={() => onChange(id)}
          onKeyDown={(e) => alTeclear(e, indice)}
        >
          {texto}
        </button>
      ))}
    </div>
  )
}
