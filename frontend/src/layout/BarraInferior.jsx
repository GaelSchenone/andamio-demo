import { Ellipsis } from 'lucide-react'
import { useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { Modal } from '../ui'
import { BARRA_INFERIOR_POR_ROL } from './navegacion'
import './BarraInferior.css'

/**
 * Navegación del celular: hasta 4 secciones y "Más" con el resto. Las secciones se identifican con
 * ícono y texto (tab-bars.md: etiquetas cortas), y la activa suma peso y marca además del color.
 */
export default function BarraInferior({ rol }) {
  const { principales, mas } = BARRA_INFERIOR_POR_ROL[rol]
  const [abierto, setAbierto] = useState(false)
  const { pathname } = useLocation()
  const navegar = useNavigate()
  const enMas = mas.some((item) => pathname.startsWith(item.ruta))

  return (
    <>
      <nav className="barra-inferior" aria-label="Principal">
        <ul>
          {principales.map(({ ruta, etiqueta, icono: Icono, fin }) => (
            <li key={ruta}>
              <NavLink to={ruta} end={fin} className="barra-inferior-enlace">
                <Icono size={22} aria-hidden="true" />
                <span>{etiqueta}</span>
              </NavLink>
            </li>
          ))}
          {mas.length > 0 && (
            <li>
              <button
                type="button"
                className={`barra-inferior-enlace${enMas ? ' is-activo' : ''}`}
                aria-haspopup="dialog"
                onClick={() => setAbierto(true)}
              >
                <Ellipsis size={22} aria-hidden="true" />
                <span>Más</span>
              </button>
            </li>
          )}
        </ul>
      </nav>
      <Modal abierto={abierto} onCerrar={() => setAbierto(false)} titulo="Más secciones" tamano="sm">
        <ul className="barra-inferior-mas">
          {mas.map(({ ruta, etiqueta, icono: Icono }) => (
            <li key={ruta}>
              <button
                type="button"
                onClick={() => {
                  setAbierto(false)
                  navegar(ruta)
                }}
              >
                <Icono size={20} aria-hidden="true" /> {etiqueta}
              </button>
            </li>
          ))}
        </ul>
      </Modal>
    </>
  )
}
