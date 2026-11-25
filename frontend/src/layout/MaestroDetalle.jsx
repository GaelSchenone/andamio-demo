import { ArrowLeft } from 'lucide-react'
import useSizeClass from '../hooks/useSizeClass'
import { Button, EmptyState } from '../ui'
import './MaestroDetalle.css'

/**
 * `fijo`: la pantalla no scrollea (ocupa el alto disponible) y el panel scrollea por dentro.
 * Lista + detalle (split-views.md). En pantallas anchas conviven: la lista a la izquierda y el detalle en
 * un panel a la derecha, con la fila elegida resaltada. En media y compacta el detalle ocupa toda la
 * pantalla y se vuelve con un botón (la URL refleja el elemento abierto, así que "atrás" también sirve).
 */
export default function MaestroDetalle({ lista, detalle, alVolver, etiquetaVolver, vacio, fijo = false }) {
  const clase = useSizeClass()
  const lado = clase === 'amplia'

  if (!lado) {
    if (!detalle) return lista
    return (
      <div className="maestro-detalle-pagina">
        <Button variante="fantasma" tamano="sm" icono={ArrowLeft} onClick={alVolver}>
          {etiquetaVolver}
        </Button>
        {detalle}
      </div>
    )
  }

  return (
    <div className={`maestro-detalle${fijo ? ' maestro-detalle--fijo' : ''}`}>
      <div className="maestro-detalle-lista">{lista}</div>
      <aside className="maestro-detalle-panel" aria-label="Detalle">
        {detalle ?? (
          <EmptyState icono={vacio.icono} titulo={vacio.titulo} texto={vacio.texto} />
        )}
      </aside>
    </div>
  )
}
