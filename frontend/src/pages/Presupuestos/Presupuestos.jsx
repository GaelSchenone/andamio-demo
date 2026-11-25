import { FileText, Plus } from 'lucide-react'
import { useCallback, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../../api'
import { pesos } from '../../constantes'
import { formatoFecha } from '../../formato'
import useCargar from '../../hooks/useCargar'
import useDebounced from '../../hooks/useDebounced'
import CabeceraPagina from '../../layout/CabeceraPagina'
import MaestroDetalle from '../../layout/MaestroDetalle'
import { Alerta, Badge, Button, EmptyState, EstadoBadge, ListaResponsiva, SearchField, Skeleton } from '../../ui'
import PresupuestoDetalle from './PresupuestoDetalle'
import './Presupuestos.css'

const COLUMNAS = [
  { id: 'numero', titulo: 'Nº', celda: (p) => p.numero },
  { id: 'cliente', titulo: 'Cliente / obra', celda: (p) => p.cliente_obra, principal: true },
  { id: 'fecha', titulo: 'Fecha', celda: (p) => formatoFecha(p.fecha_emision) },
  {
    id: 'estado',
    titulo: 'Estado',
    celda: (p) => (
      <span className="presupuestos-estados">
        <EstadoBadge tipo="presupuesto" estado={p.estado} />
        {p.trabajo_id && <Badge>Con trabajo</Badge>}
      </span>
    ),
  },
  { id: 'total', titulo: 'Total', celda: (p) => pesos(p.total), alinear: 'der' },
]

export default function Presupuestos() {
  const { id } = useParams()
  const navegar = useNavigate()
  const [buscar, setBuscar] = useState('')
  const texto = useDebounced(buscar)
  const { datos, error, cargando, recargar } = useCargar(useCallback(() => api.listarPresupuestos(texto), [texto]), [texto])

  const lista = (
    <>
      <CabeceraPagina
        titulo="Presupuestos"
        subtitulo="Armalos, mandalos en PDF y pasalos a trabajo."
        acciones={
          <Button variante="primario" icono={Plus} onClick={() => navegar('/presupuestos/nuevo')}>
            Nuevo presupuesto
          </Button>
        }
      />
      <SearchField etiqueta="Buscar presupuestos" valor={buscar} onChange={setBuscar} placeholder="Buscar por cliente u obra…" className="presupuestos-buscar" />
      {error && <Alerta>{error}</Alerta>}
      {cargando && !datos ? (
        <div aria-busy="true">
          <Skeleton alto="3rem" />
        </div>
      ) : datos?.length === 0 ? (
        <EmptyState
          icono={FileText}
          titulo={texto ? 'No encontramos presupuestos' : 'Todavía no creaste presupuestos'}
          texto={texto ? 'Probá con otro nombre de cliente.' : 'Los que generes van a aparecer acá para que los busques cuando quieras.'}
          accion={!texto && <Button variante="primario" icono={Plus} onClick={() => navegar('/presupuestos/nuevo')}>Crear el primero</Button>}
        />
      ) : (
        datos && (
          <ListaResponsiva
            nombre="Presupuestos"
            filas={datos}
            columnas={COLUMNAS}
            claveDe={(p) => String(p.id)}
            seleccionada={id}
            alElegir={(p) => navegar(`/presupuestos/${p.id}`)}
            etiquetaDe={(p) => `Presupuesto Nº ${p.numero}, ${p.cliente_obra}`}
          />
        )
      )}
    </>
  )

  return (
    <MaestroDetalle
      lista={lista}
      detalle={id ? <PresupuestoDetalle key={id} id={id} alCambiar={recargar} alEliminar={() => { recargar(); navegar('/presupuestos') }} /> : null}
      alVolver={() => navegar('/presupuestos')}
      etiquetaVolver="Presupuestos"
      vacio={{ icono: FileText, titulo: 'Elegí un presupuesto', texto: 'Ves el detalle, cambiás el estado y sacás el PDF acá.' }}
    />
  )
}
