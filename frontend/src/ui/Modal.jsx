import { X } from 'lucide-react'
import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import { atraparTab, enfocarAlAbrir } from '../hooks/useFocusTrap'
import IconButton from './IconButton'
import { apilar, desapilar, esLaDeArriba } from './pilaDeVentanas'
import './Modal.css'

/**
 * Ventana para una tarea corta (modality.md, sheets.md). Es un diálogo centrado en pantallas anchas y
 * una hoja que sube desde abajo en celular; el mismo componente, el CSS decide la presentación.
 *
 * Garantías: título que nombra la tarea, foco que entra y no se escapa (Tab), Escape cierra, el foco
 * vuelve a donde estaba, el fondo no scrollea ni recibe foco, y siempre hay una salida obvia: el botón
 * de cerrar (además del gesto de deslizar en la hoja, que nunca es la única forma).
 *
 * `cerrarAlTocarFuera`: pasar false si hay cambios sin guardar. `pie`: botones de acción (sticky).
 * Para marcar con qué elemento arranca el foco, ponerle `data-autofocus`.
 */
export default function Modal({ abierto, ...resto }) {
  if (!abierto) return null
  return createPortal(<Ventana {...resto} />, document.body)
}

const DESLIZAR_PARA_CERRAR_PX = 96

function Ventana({ onCerrar, titulo, descripcion, tamano = 'md', cerrarAlTocarFuera = true, pie, children }) {
  const idTitulo = useId()
  const idDescripcion = useId()
  const ventana = useRef(null)
  const cuerpo = useRef(null)
  const alCerrar = useRef(onCerrar)
  const arrastre = useRef(null)

  useEffect(() => {
    alCerrar.current = onCerrar
  })

  useEffect(() => {
    const idVentana = apilar()
    const previo = document.activeElement
    enfocarAlAbrir(ventana.current, cuerpo.current)

    function alTeclear(evento) {
      if (!esLaDeArriba(idVentana)) return
      if (evento.key === 'Escape') {
        evento.preventDefault()
        alCerrar.current()
        return
      }
      atraparTab(evento, ventana.current)
    }
    document.addEventListener('keydown', alTeclear)

    return () => {
      document.removeEventListener('keydown', alTeclear)
      desapilar(idVentana) // primero se libera el fondo (deja de ser inerte)…
      if (previo && document.contains(previo)) previo.focus() // …y recién ahí vuelve el foco
    }
  }, [])

  function alTocarElFondo(evento) {
    if (cerrarAlTocarFuera && evento.target === evento.currentTarget) alCerrar.current()
  }

  // Deslizar hacia abajo desde la manija (solo existe en la hoja de celular).
  function empezarArrastre(evento) {
    arrastre.current = { desde: evento.clientY, distancia: 0 }
    evento.currentTarget.setPointerCapture(evento.pointerId)
  }
  function moverArrastre(evento) {
    if (!arrastre.current) return
    const distancia = Math.max(0, evento.clientY - arrastre.current.desde)
    arrastre.current.distancia = distancia
    ventana.current.style.transition = 'none'
    ventana.current.style.transform = `translateY(${distancia}px)`
  }
  function soltarArrastre() {
    if (!arrastre.current) return
    const { distancia } = arrastre.current
    arrastre.current = null
    ventana.current.style.transition = ''
    if (distancia > DESLIZAR_PARA_CERRAR_PX) alCerrar.current()
    else ventana.current.style.transform = ''
  }

  return (
    <div className="ui-modal-fondo" onMouseDown={alTocarElFondo}>
      <div
        ref={ventana}
        className={`ui-modal ui-modal--${tamano}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        aria-describedby={descripcion ? idDescripcion : undefined}
        tabIndex={-1}
      >
        <div
          className="ui-modal-manija"
          aria-hidden="true"
          onPointerDown={empezarArrastre}
          onPointerMove={moverArrastre}
          onPointerUp={soltarArrastre}
          onPointerCancel={soltarArrastre}
        />
        <header className="ui-modal-cab">
          <h2 id={idTitulo} className="ui-modal-titulo">
            {titulo}
          </h2>
          <IconButton icono={X} etiqueta="Cerrar" onClick={() => alCerrar.current()} />
        </header>
        <div ref={cuerpo} className="ui-modal-cuerpo">
          {descripcion && (
            <p id={idDescripcion} className="ui-modal-descripcion">
              {descripcion}
            </p>
          )}
          {children}
        </div>
        {pie && <footer className="ui-modal-pie">{pie}</footer>}
      </div>
    </div>
  )
}
