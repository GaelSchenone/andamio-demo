import { NavLink } from 'react-router-dom'
import Marca from './Marca'
import { GRUPOS_POR_ROL } from './navegacion'
import './BarraLateral.css'

/**
 * Navegación lateral. `modo="completa"` (≥ 1024 px): 240 px con grupos y etiquetas.
 * `modo="riel"` (720–1023 px): solo íconos con la etiqueta como tooltip y para lectores de pantalla.
 * Dos niveles como máximo (grupo → sección), como pide sidebars.md.
 */
export default function BarraLateral({ rol, modo }) {
  return (
    <nav className={`barra-lateral barra-lateral--${modo}`} aria-label="Principal">
      <div className="barra-lateral-marca">
        <Marca variante="icono" ancho={28} />
        {modo === 'completa' && <span className="barra-lateral-nombre">obras demo</span>}
      </div>
      {GRUPOS_POR_ROL[rol].map((grupo, i) => (
        <div className="barra-lateral-grupo" key={grupo.titulo ?? i}>
          {grupo.titulo && modo === 'completa' && <p className="barra-lateral-titulo">{grupo.titulo}</p>}
          {grupo.titulo && modo === 'riel' && <hr className="barra-lateral-separador" />}
          <ul>
            {grupo.items.map(({ ruta, etiqueta, icono: Icono, fin }) => (
              <li key={ruta}>
                <NavLink
                  to={ruta}
                  end={fin}
                  className="barra-lateral-enlace"
                  aria-label={modo === 'riel' ? etiqueta : undefined}
                  data-etiqueta={etiqueta}
                >
                  <Icono size={20} aria-hidden="true" />
                  {modo === 'completa' && <span>{etiqueta}</span>}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  )
}
