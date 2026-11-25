import './CabeceraPagina.css'

/** Título de la pantalla (en la fuente de cartel), una línea de contexto y las acciones principales. */
export default function CabeceraPagina({ titulo, subtitulo, acciones }) {
  return (
    <div className="cabecera-pagina">
      <div>
        <h1>{titulo}</h1>
        {subtitulo && <p>{subtitulo}</p>}
      </div>
      {acciones && <div className="cabecera-pagina-acciones">{acciones}</div>}
    </div>
  )
}
