import { CircleCheck, TriangleAlert, X } from 'lucide-react'
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import IconButton from './IconButton'
import './Toast.css'

const Contexto = createContext(null)

const SE_CIERRA_SOLO_MS = 6000
const MAXIMO_VISIBLES = 3

/**
 * Avisos breves ("Cliente guardado"). Los de éxito se cierran solos a los 6 s; los errores se quedan
 * hasta que alguien los cierre (accessibility.md › Cognitive: minimizar lo que desaparece por tiempo).
 * Todos tienen botón de cerrar. La región es aria-live: los lectores de pantalla anuncian cada aviso.
 */
export function ToastProvider({ children }) {
  const [avisos, setAvisos] = useState([])
  const contador = useRef(0)

  const cerrar = useCallback((id) => setAvisos((lista) => lista.filter((a) => a.id !== id)), [])

  const avisar = useCallback((mensaje, { tono = 'ok' } = {}) => {
    contador.current += 1
    setAvisos((lista) => [...lista.slice(-(MAXIMO_VISIBLES - 1)), { id: contador.current, mensaje, tono }])
  }, [])

  return (
    <Contexto.Provider value={avisar}>
      {children}
      <div className="ui-avisos" role="region" aria-label="Avisos" aria-live="polite">
        {avisos.map((aviso) => (
          <Aviso key={aviso.id} {...aviso} onCerrar={() => cerrar(aviso.id)} />
        ))}
      </div>
    </Contexto.Provider>
  )
}

function Aviso({ mensaje, tono, onCerrar }) {
  const esError = tono === 'peligro'
  const Icono = esError ? TriangleAlert : CircleCheck

  useEffect(() => {
    if (esError) return undefined
    const temporizador = setTimeout(onCerrar, SE_CIERRA_SOLO_MS)
    return () => clearTimeout(temporizador)
  }, [esError, onCerrar])

  return (
    <div className={`ui-aviso ui-aviso--${tono}`} role={esError ? 'alert' : 'status'}>
      <Icono size={20} aria-hidden="true" />
      <p>{mensaje}</p>
      <IconButton icono={X} etiqueta="Cerrar aviso" tamano={18} onClick={onCerrar} />
    </div>
  )
}

/** `avisar('Guardado')` o `avisar('No se pudo guardar', { tono: 'peligro' })`. */
export function useAvisar() {
  const avisar = useContext(Contexto)
  if (!avisar) throw new Error('useAvisar necesita estar dentro de <ToastProvider>.')
  return avisar
}
