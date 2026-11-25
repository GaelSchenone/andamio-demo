import './Segmentado.css'

/** Control de 2 a 4 opciones excluyentes (por ejemplo Lista | Calendario). Botones con aria-pressed. */
export default function Segmentado({ opciones, valor, onChange, etiqueta, className = '' }) {
  return (
    <div className={`ui-segmentado ${className}`.trim()} role="group" aria-label={etiqueta}>
      {opciones.map(({ valor: v, etiqueta: texto, icono: Icono }) => (
        <button
          key={v}
          type="button"
          className={valor === v ? 'is-activo' : undefined}
          aria-pressed={valor === v}
          onClick={() => onChange(v)}
        >
          {Icono && <Icono size={16} aria-hidden="true" />}
          {texto}
        </button>
      ))}
    </div>
  )
}
