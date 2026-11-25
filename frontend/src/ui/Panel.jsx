import { useId } from 'react'
import './Panel.css'

/** Superficie con cabecera opcional (título + acciones). Es la unidad con la que se arma un dashboard. */
export default function Panel({ titulo, icono: Icono, acciones, children, className = '', ...resto }) {
  const idTitulo = useId()
  return (
    <section
      className={`ui-panel ${className}`.trim()}
      aria-labelledby={titulo ? idTitulo : undefined}
      {...resto}
    >
      {(titulo || acciones) && (
        <header className="ui-panel-cab">
          {titulo && (
            <h2 id={idTitulo} className="ui-panel-titulo">
              {Icono && <Icono size={18} aria-hidden="true" />}
              {titulo}
            </h2>
          )}
          {acciones && <div className="ui-panel-acciones">{acciones}</div>}
        </header>
      )}
      <div className="ui-panel-cuerpo">{children}</div>
    </section>
  )
}
