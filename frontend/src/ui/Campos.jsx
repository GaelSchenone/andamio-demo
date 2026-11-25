import { useId } from 'react'
import './Campos.css'

// Cada campo une etiqueta, ayuda y error con el control (htmlFor, aria-describedby, aria-invalid),
// así un lector de pantalla anuncia "Teléfono, edición, formato inválido" y no un cuadro sin nombre.
function Campo({ etiqueta, ayuda, error, opcional, children, id, idAyuda, idError }) {
  return (
    <div className={`ui-campo${error ? ' ui-campo--error' : ''}`}>
      <label htmlFor={id} className="ui-campo-etiqueta">
        {etiqueta}
        {opcional && <span className="ui-campo-opcional"> (opcional)</span>}
      </label>
      {children}
      {ayuda && !error && (
        <p id={idAyuda} className="ui-campo-ayuda">
          {ayuda}
        </p>
      )}
      {error && (
        <p id={idError} className="ui-campo-mensaje" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

function useCampo({ ayuda, error, id: idPropio }) {
  const base = useId()
  const id = idPropio ?? base
  const idAyuda = `${id}-ayuda`
  const idError = `${id}-error`
  const describedBy = error ? idError : ayuda ? idAyuda : undefined
  return { id, idAyuda, idError, describedBy }
}

export function Input({ etiqueta, ayuda, error, opcional, className = '', ...resto }) {
  const { id, idAyuda, idError, describedBy } = useCampo({ ayuda, error, id: resto.id })
  return (
    <Campo {...{ etiqueta, ayuda, error, opcional, id, idAyuda, idError }}>
      <input
        {...resto}
        id={id}
        className={`ui-control ${className}`.trim()}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
      />
    </Campo>
  )
}

export function Select({ etiqueta, ayuda, error, opcional, className = '', children, ...resto }) {
  const { id, idAyuda, idError, describedBy } = useCampo({ ayuda, error, id: resto.id })
  return (
    <Campo {...{ etiqueta, ayuda, error, opcional, id, idAyuda, idError }}>
      <select
        {...resto}
        id={id}
        className={`ui-control ui-control--select ${className}`.trim()}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
      >
        {children}
      </select>
    </Campo>
  )
}

export function Textarea({ etiqueta, ayuda, error, opcional, className = '', rows = 3, ...resto }) {
  const { id, idAyuda, idError, describedBy } = useCampo({ ayuda, error, id: resto.id })
  return (
    <Campo {...{ etiqueta, ayuda, error, opcional, id, idAyuda, idError }}>
      <textarea
        {...resto}
        id={id}
        rows={rows}
        className={`ui-control ${className}`.trim()}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
      />
    </Campo>
  )
}
