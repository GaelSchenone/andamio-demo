import './EmptyState.css'

/** Estado vacío: dice qué pasa y, si hay, invita a la próxima acción (writing.md: "Empty screens invite the next action"). */
export default function EmptyState({ icono: Icono, titulo, texto, accion }) {
  return (
    <div className="ui-vacio">
      {Icono && <Icono size={40} aria-hidden="true" className="ui-vacio-icono" />}
      <p className="ui-vacio-titulo">{titulo}</p>
      {texto && <p className="ui-vacio-texto">{texto}</p>}
      {accion && <div className="ui-vacio-accion">{accion}</div>}
    </div>
  )
}
