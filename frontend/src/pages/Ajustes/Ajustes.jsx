import { useNavigate, useParams } from 'react-router-dom'
import CabeceraPagina from '../../layout/CabeceraPagina'
import { useSesion } from '../../layout/sesion'
import { Tabs } from '../../ui'
import MiCuenta from './MiCuenta'
import Usuarios from './Usuarios'

export default function Ajustes() {
  const { esDueno } = useSesion()
  const { seccion } = useParams()
  const navegar = useNavigate()
  const activa = esDueno && seccion === 'usuarios' ? 'usuarios' : 'cuenta'
  const pestanas = [
    { id: 'cuenta', etiqueta: 'Mi cuenta' },
    ...(esDueno ? [{ id: 'usuarios', etiqueta: 'Usuarios' }] : []),
  ]

  return (
    <>
      <CabeceraPagina titulo="Ajustes" />
      {pestanas.length > 1 && (
        <Tabs
          etiqueta="Ajustes"
          pestanas={pestanas}
          activa={activa}
          onChange={(id) => navegar(id === 'cuenta' ? '/ajustes' : `/ajustes/${id}`)}
        />
      )}
      <div role="tabpanel" id={`panel-${activa}`} aria-labelledby={`pestana-${activa}`} className="ajustes-panel">
        {activa === 'cuenta' ? <MiCuenta /> : <Usuarios />}
      </div>
    </>
  )
}
