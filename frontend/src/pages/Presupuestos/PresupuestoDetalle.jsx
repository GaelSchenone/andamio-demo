import { FileDown, HardHat, Pencil, Trash2 } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api'
import { formatoCantidad, pesos } from '../../constantes'
import { ESTADOS_PRESUPUESTO } from '../../estados'
import { formatoFecha } from '../../formato'
import useCargar from '../../hooks/useCargar'
import { Alerta, Button, EstadoBadge, Select, Skeleton, useAvisar, useConfirmar } from '../../ui'
import './Presupuestos.css'

export default function PresupuestoDetalle({ id, alCambiar, alEliminar }) {
  const avisar = useAvisar()
  const confirmar = useConfirmar()
  const navegar = useNavigate()
  const { datos: p, error, setDatos } = useCargar(useCallback(() => api.obtenerPresupuesto(id), [id]), [id])
  const [ocupado, setOcupado] = useState(false)

  // Corre una acción mostrando el mensaje del servidor si una regla la frena.
  async function accion(hacer) {
    setOcupado(true)
    try {
      await hacer()
    } catch (err) {
      avisar(err.message, { tono: 'peligro' })
    } finally {
      setOcupado(false)
    }
  }

  const cambiarEstado = (estado) =>
    accion(async () => {
      const actualizado = await api.cambiarEstadoPresupuesto(id, estado)
      setDatos((d) => ({ ...d, estado: actualizado.estado, trabajo_id: actualizado.trabajo_id }))
      avisar(`Presupuesto Nº ${p.numero}: ahora está ${ESTADOS_PRESUPUESTO[estado].toLowerCase()}.`)
      alCambiar()
    })

  const pasarATrabajo = () =>
    accion(async () => {
      const trabajo = await api.pasarATrabajo(id)
      setDatos((d) => ({ ...d, trabajo_id: trabajo.id }))
      avisar('Se creó el trabajo. Ya podés agendarlo.')
      alCambiar()
    })

  async function eliminar() {
    const si = await confirmar({
      titulo: '¿Eliminar el presupuesto?',
      mensaje: `${p.cliente_obra}. Esta acción no se puede deshacer.`,
      confirmarLabel: 'Eliminar presupuesto',
      peligro: true,
    })
    if (!si) return
    accion(async () => {
      await api.eliminarPresupuesto(id)
      avisar('Presupuesto eliminado.')
      alEliminar()
    })
  }

  if (error) return <Alerta>{error}</Alerta>
  if (!p) return <Skeleton alto="8rem" />

  const aprobado = p.estado === 'aprobado'
  const motivo = 'Un presupuesto aprobado no se modifica: cambiale el estado primero.'

  return (
    <div className="presupuesto-detalle">
      <header className="presupuesto-encabezado">
        <p className="presupuesto-numero">Presupuesto Nº {p.numero}</p>
        <h2>{p.cliente_obra}</h2>
        <p className="presupuesto-sub">
          {p.direccion && `${p.direccion} · `}
          {formatoFecha(p.fecha_emision)} · vigencia {p.vigencia_dias} días
        </p>
        <div>
          <EstadoBadge tipo="presupuesto" estado={p.estado} />
        </div>
      </header>

      <section aria-labelledby={`items-${p.id}`}>
        <h3 id={`items-${p.id}`}>Trabajos</h3>
        <ul className="presupuesto-items">
          {p.items.map((it) => (
            <li key={it.id}>
              <span>
                {it.descripcion}
                {it.unidad && <small>{formatoCantidad(it.cantidad)} {it.unidad}</small>}
              </span>
              <strong>{pesos(it.importe)}</strong>
            </li>
          ))}
        </ul>
        <p className="presupuesto-total">
          <span>Total</span>
          <strong>{pesos(p.total)}</strong>
        </p>
        <p className="presupuesto-sub">
          Pago: {p.forma_pago} · Materiales: {p.materiales_a_cargo}
          {p.plazo_obra && ` · Plazo: ${p.plazo_obra}`}
        </p>
      </section>

      <section className="presupuesto-estado">
        <Select etiqueta="Estado" value={p.estado} disabled={ocupado} onChange={(e) => cambiarEstado(e.target.value)}>
          {Object.entries(ESTADOS_PRESUPUESTO).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </Select>
        {aprobado && !p.trabajo_id && (
          <Button variante="primario" icono={HardHat} disabled={ocupado} onClick={pasarATrabajo}>
            Pasar a trabajo
          </Button>
        )}
        {p.trabajo_id && (
          <Link className="ui-btn ui-btn--secundario ui-btn--md" to={`/trabajos/${p.trabajo_id}`}>
            <HardHat size={18} aria-hidden="true" /> Ver el trabajo
          </Link>
        )}
      </section>

      <div className="presupuesto-acciones">
        <a className="ui-btn ui-btn--secundario ui-btn--md" href={api.urlPdf(p.id)} target="_blank" rel="noopener noreferrer">
          <FileDown size={18} aria-hidden="true" /> Ver PDF
        </a>
        <Button icono={Pencil} disabled={aprobado} title={aprobado ? motivo : undefined} onClick={() => navegar(`/presupuestos/${p.id}/editar`)}>
          Editar
        </Button>
        <Button variante="peligro" icono={Trash2} disabled={ocupado || aprobado} title={aprobado ? motivo : undefined} onClick={eliminar}>
          Eliminar
        </Button>
      </div>
      {aprobado && <Alerta tono="info">{motivo}</Alerta>}
    </div>
  )
}
