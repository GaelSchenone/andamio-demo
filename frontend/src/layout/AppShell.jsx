import { Outlet } from 'react-router-dom'
import useSizeClass from '../hooks/useSizeClass'
import AgenteChat from './agente/AgenteChat'
import BarraInferior from './BarraInferior'
import BarraLateral from './BarraLateral'
import Marca from './Marca'
import MenuUsuario from './MenuUsuario'
import { useSesion } from './sesion'
import './AppShell.css'

/**
 * Estructura de la app según el espacio (layout.md › Size classes): barra lateral completa en pantallas
 * anchas, riel de íconos en las medias y barra inferior en celular. Mismas secciones en las tres.
 */
export default function AppShell({ onSalir }) {
  const { yo } = useSesion()
  const clase = useSizeClass()

  return (
    <div className={`shell shell--${clase}`}>
      <a className="skip-link" href="#contenido">
        Saltar al contenido
      </a>
      {clase !== 'compacta' && <BarraLateral rol={yo.rol} modo={clase === 'amplia' ? 'completa' : 'riel'} />}
      <div className="shell-columna">
        <header className="shell-superior">
          {clase === 'compacta' && (
            <Marca variante="icono" ancho={32} />
          )}
          <span className="shell-superior-relleno" />
          <MenuUsuario onSalir={onSalir} />
        </header>
        <main id="contenido" className="shell-contenido" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
      {clase === 'compacta' && <BarraInferior rol={yo.rol} />}
      <AgenteChat />
    </div>
  )
}
