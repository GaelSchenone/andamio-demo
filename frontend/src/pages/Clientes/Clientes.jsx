import { Plus, Users } from 'lucide-react'
import { useCallback, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../../api'
import useCargar from '../../hooks/useCargar'
import useDebounced from '../../hooks/useDebounced'
import CabeceraPagina from '../../layout/CabeceraPagina'
import MaestroDetalle from '../../layout/MaestroDetalle'
import { useSesion } from '../../layout/sesion'
import { TIPOS_CLIENTE } from '../../constantes'
import { Alerta, Badge, Button, EmptyState, ListaResponsiva, SearchField, Skeleton } from '../../ui'
import ClienteDetalle from './ClienteDetalle'
import ClienteFormulario from './ClienteFormulario'
import './Clientes.css'

const COLUMNAS = [
  { id: 'nombre', titulo: 'Cliente', celda: (c) => c.nombre, principal: true },
  { id: 'tipo', titulo: 'Tipo', celda: (c) => <Badge>{TIPOS_CLIENTE[c.tipo]}</Badge> },
  { id: 'telefono', titulo: 'Teléfono', celda: (c) => c.telefono || '—' },
  { id: 'obras', titulo: 'Obras', celda: (c) => c.cantidad_obras, alinear: 'der' },
]

export default function Clientes() {
  const { esDueno } = useSesion()
  const { id } = useParams()
  const navegar = useNavigate()
  const [buscar, setBuscar] = useState('')
  const texto = useDebounced(buscar)
  const [creando, setCreando] = useState(false)
  const { datos: clientes, error, cargando, recargar } = useCargar(
    useCallback(() => api.listarClientes(texto), [texto]),
    [texto]
  )

  const lista = (
    <>
      <CabeceraPagina
        titulo="Clientes"
        subtitulo="Con sus direcciones de obra."
        acciones={
          esDueno && (
            <Button variante="primario" icono={Plus} onClick={() => setCreando(true)}>
              Nuevo cliente
            </Button>
          )
        }
      />
      <SearchField etiqueta="Buscar clientes" valor={buscar} onChange={setBuscar} placeholder="Buscar por nombre, teléfono o dirección…" className="clientes-buscar" />
      {error && <Alerta>{error}</Alerta>}
      {cargando && !clientes ? (
        <div className="clientes-cargando" aria-busy="true">
          <Skeleton alto="3rem" />
          <Skeleton alto="3rem" />
          <Skeleton alto="3rem" />
        </div>
      ) : clientes?.length === 0 ? (
        <EmptyState
          icono={Users}
          titulo={texto ? 'No encontramos clientes' : 'Todavía no hay clientes'}
          texto={texto ? 'Probá con otro nombre, teléfono o dirección.' : esDueno ? 'Cargá el primero con el botón de arriba.' : 'Cuando el dueño los cargue, los vas a ver acá.'}
        />
      ) : (
        clientes && (
          <ListaResponsiva
            nombre="Clientes"
            filas={clientes}
            columnas={COLUMNAS}
            claveDe={(c) => String(c.id)}
            seleccionada={id}
            alElegir={(c) => navegar(`/clientes/${c.id}`)}
          />
        )
      )}
    </>
  )

  return (
    <>
      <MaestroDetalle
        lista={lista}
        detalle={id ? <ClienteDetalle key={id} id={id} alCambiar={recargar} alEliminar={() => { recargar(); navegar('/clientes') }} /> : null}
        alVolver={() => navegar('/clientes')}
        etiquetaVolver="Clientes"
        vacio={{ icono: Users, titulo: 'Elegí un cliente', texto: 'Ves sus datos y sus obras acá.' }}
      />
      <ClienteFormulario
        abierto={creando}
        onCerrar={() => setCreando(false)}
        onGuardado={(nuevo) => {
          setCreando(false)
          recargar()
          navegar(`/clientes/${nuevo.id}`)
        }}
      />
    </>
  )
}
