import './Kpi.css'

/**
 * Indicador: un número grande con su etiqueta. Si recibe `onClick` es un botón (lleva a algún lado);
 * si no, es solo información. El número va con cifras tabulares para que no "salte" al cambiar.
 */
export default function Kpi({ etiqueta, valor, ayuda, icono: Icono, onClick }) {
  const contenido = (
    <>
      <span className="ui-kpi-etiqueta">
        {Icono && <Icono size={16} aria-hidden="true" />}
        {etiqueta}
      </span>
      <span className="ui-kpi-valor">{valor}</span>
      {ayuda && <span className="ui-kpi-ayuda">{ayuda}</span>}
    </>
  )
  return onClick ? (
    <button type="button" className="ui-kpi ui-kpi--accion" onClick={onClick}>
      {contenido}
    </button>
  ) : (
    <div className="ui-kpi">{contenido}</div>
  )
}
