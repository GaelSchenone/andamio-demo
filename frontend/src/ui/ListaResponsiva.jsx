import useSizeClass from '../hooks/useSizeClass'
import './ListaResponsiva.css'

/**
 * Datos en filas: tabla desde 720 px y tarjetas en celular (nada de scroll horizontal).
 *
 * `columnas`: [{ id, titulo, celda(fila), principal?, alinear?, ocultarEnTarjeta? }]. La columna `principal`
 * es el botón que abre la fila (toda la fila es clickeable, pero el foco y el lector de pantalla
 * encuentran ese botón). `seleccionada` resalta la fila abierta con aria-current: en pantallas anchas
 * la lista convive con el panel de detalle y hay que ver cuál se está mirando (split-views.md).
 */
export default function ListaResponsiva({
  nombre,
  filas,
  columnas,
  claveDe,
  seleccionada,
  alElegir,
  etiquetaDe,
}) {
  const clase = useSizeClass()
  const principal = columnas.find((c) => c.principal) ?? columnas[0]

  const abrir = (fila) => (
    <button
      type="button"
      className="ui-lista-abrir"
      aria-current={claveDe(fila) === seleccionada ? 'true' : undefined}
      aria-label={etiquetaDe ? etiquetaDe(fila) : undefined}
      onClick={() => alElegir?.(fila)}
    >
      {principal.celda(fila)}
    </button>
  )

  if (clase === 'compacta') {
    return (
      <ul className="ui-tarjetas" aria-label={nombre}>
        {filas.map((fila) => (
          <li
            key={claveDe(fila)}
            className={`ui-tarjeta${claveDe(fila) === seleccionada ? ' is-elegida' : ''}`}
          >
            <div className="ui-tarjeta-titulo">{abrir(fila)}</div>
            <dl className="ui-tarjeta-datos">
              {columnas
                .filter((c) => c !== principal && !c.ocultarEnTarjeta)
                .map((c) => (
                  <div key={c.id}>
                    <dt>{c.titulo}</dt>
                    <dd>{c.celda(fila)}</dd>
                  </div>
                ))}
            </dl>
          </li>
        ))}
      </ul>
    )
  }

  return (
    <table className="ui-tabla" aria-label={nombre}>
      <thead>
        <tr>
          {columnas.map((c) => (
            <th key={c.id} scope="col" className={c.alinear === 'der' ? 'es-der' : undefined}>
              {c.titulo}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {filas.map((fila) => (
          <tr key={claveDe(fila)} className={claveDe(fila) === seleccionada ? 'is-elegida' : undefined}>
            {columnas.map((c) => (
              <td key={c.id} className={c.alinear === 'der' ? 'es-der' : undefined}>
                {c === principal ? abrir(fila) : c.celda(fila)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
