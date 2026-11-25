import { Wallet } from 'lucide-react'
import { useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../../api'
import { pesos } from '../../constantes'
import useCargar from '../../hooks/useCargar'
import { formatoFecha } from '../../formato'
import CabeceraPagina from '../../layout/CabeceraPagina'
import MaestroDetalle from '../../layout/MaestroDetalle'
import { Alerta, EmptyState, EstadoBadge, Kpi, ListaResponsiva, Skeleton } from '../../ui'
import CobrosDelTrabajo from './CobrosDelTrabajo'
import './Cobros.css'

const COLUMNAS = [
  { id: 'cliente', titulo: 'Cliente', celda: (t) => t.cliente, principal: true },
  {
    id: 'obra',
    titulo: 'Obra',
    celda: (t) => (
      <>
        {t.direccion}
        {t.referencia ? ` · ${t.referencia}` : ''}
      </>
    ),
  },
  { id: 'estado', titulo: 'Estado', celda: (t) => <EstadoBadge estado={t.estado} /> },
  { id: 'pendiente', titulo: 'Falta', celda: (t) => pesos(t.pendiente), alinear: 'der' },
]

// Quién me debe plata: los trabajos a los que todavía les falta cobrar algo. Primero los ya terminados.
export default function Cobros() {
  const { trabajoId } = useParams()
  const navegar = useNavigate()
  const { datos, error, recargar } = useCargar(useCallback(() => api.cobrosPendientes(), []))
  const elegido = datos?.trabajos.find((t) => String(t.trabajo_id) === trabajoId)

  const lista = (
    <>
      <CabeceraPagina titulo="Cobros" subtitulo="Lo que todavía falta cobrar." />
      {error && <Alerta>{error}</Alerta>}
      {!datos && !error && <Skeleton alto="6rem" />}
      {datos && (
        <>
          <div className="cobros-pendiente">
            <Kpi etiqueta="Falta cobrar en total" valor={pesos(datos.total_pendiente)} icono={Wallet} />
          </div>
          {datos.trabajos.length === 0 ? (
            <EmptyState icono={Wallet} titulo="No hay nada pendiente de cobro" texto="Los trabajos con saldo por cobrar van a aparecer acá." />
          ) : (
            <ListaResponsiva
              nombre="Trabajos con saldo pendiente"
              filas={datos.trabajos}
              columnas={COLUMNAS}
              claveDe={(t) => String(t.trabajo_id)}
              seleccionada={trabajoId}
              alElegir={(t) => navegar(`/cobros/${t.trabajo_id}`)}
            />
          )}
        </>
      )}
    </>
  )

  const detalle =
    trabajoId && datos ? (
      <div>
        {elegido && (
          <div className="cobros-detalle-cab">
            <h2>{elegido.cliente}</h2>
            <p>
              {elegido.direccion}
              {elegido.fecha_inicio ? ` · ${formatoFecha(elegido.fecha_inicio)}` : ''}
            </p>
            <div>
              <EstadoBadge estado={elegido.estado} />
            </div>
          </div>
        )}
        <CobrosDelTrabajo key={trabajoId} trabajoId={trabajoId} alCambiar={recargar} />
      </div>
    ) : null

  return (
    <MaestroDetalle
      lista={lista}
      detalle={detalle}
      alVolver={() => navegar('/cobros')}
      etiquetaVolver="Cobros"
      vacio={{ icono: Wallet, titulo: 'Elegí un trabajo', texto: 'Ves lo cobrado y registrás pagos acá.' }}
    />
  )
}
