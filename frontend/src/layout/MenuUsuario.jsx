import { LogOut, Settings } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ROLES } from '../constantes'
import { Avatar } from '../ui'
import { useSesion } from './sesion'
import './MenuUsuario.css'

/** Avatar que abre un menú con la cuenta y "Cerrar sesión" (nada crítico queda al pie de la barra). */
export default function MenuUsuario({ onSalir }) {
  const { yo } = useSesion()
  const [abierto, setAbierto] = useState(false)
  const raiz = useRef(null)
  const idMenu = useId()
  const navegar = useNavigate()

  useEffect(() => {
    if (!abierto) return undefined
    const cerrarSiEsFuera = (e) => !raiz.current?.contains(e.target) && setAbierto(false)
    const cerrarConEscape = (e) => {
      if (e.key !== 'Escape') return
      setAbierto(false)
      raiz.current?.querySelector('button')?.focus()
    }
    document.addEventListener('mousedown', cerrarSiEsFuera)
    document.addEventListener('keydown', cerrarConEscape)
    return () => {
      document.removeEventListener('mousedown', cerrarSiEsFuera)
      document.removeEventListener('keydown', cerrarConEscape)
    }
  }, [abierto])

  return (
    <div className="menu-usuario" ref={raiz}>
      <button
        type="button"
        className="menu-usuario-boton"
        aria-expanded={abierto}
        aria-controls={abierto ? idMenu : undefined}
        aria-label={`Cuenta de ${yo.nombre}`}
        onClick={() => setAbierto((v) => !v)}
      >
        <Avatar nombre={yo.nombre} />
      </button>
      {abierto && (
        <div className="menu-usuario-panel" id={idMenu}>
          <div className="menu-usuario-quien">
            <strong>{yo.nombre}</strong>
            <span>
              @{yo.usuario} · {ROLES[yo.rol]}
            </span>
          </div>
          <button
            type="button"
            onClick={() => {
              setAbierto(false)
              navegar('/ajustes')
            }}
          >
            <Settings size={18} aria-hidden="true" /> Mi cuenta
          </button>
          <button type="button" onClick={onSalir}>
            <LogOut size={18} aria-hidden="true" /> Cerrar sesión
          </button>
        </div>
      )}
    </div>
  )
}
