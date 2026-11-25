import { CalendarClock, CalendarPlus, MapPin, Phone, SquareCheckBig, XCircle } from 'lucide-react'
import { useState } from 'react'
import { api } from '../../api'
import { formatoCantidad, textoDeFechas } from '../../constantes'
import { urlMapa, urlTelefono } from '../../enlaces'
import { useSesion } from '../../layout/sesion'
import { Button, EstadoBadge, useAvisar, useConfirmar } from '../../ui'
import './Trabajos.css'

/**
 * Un trabajo con todo lo que se puede hacer con él. Lo que se ofrece depende del estado y del rol; el
 * servidor igual vuelve a controlarlo todo, y si una regla lo frena se muestra su mensaje.
 * Un empleado nunca ve precios: este componente no los recibe (los trabajos vienen sin plata).
 */
export default function TrabajoDetalle({ trabajo: t, alCambiar, alElegirDias }) {
  const { esDueno } = useSesion()
  const avisar = useAvisar()
  const confirmar = useConfirmar()
  const [ocupado, setOcupado] = useState(false)

  const puedeAgendar = esDueno && t.estado === 'por_agendar'
  const puedeReprogramar = esDueno && (t.estado === 'agendado' || t.estado === 'en_curso')
  const puedeTerminar = t.estado === 'agendado' || t.estado === 'en_curso'
  const puedeCancelar = esDueno && (t.estado === 'por_agendar' || t.estado === 'agendado')

  async function ejecutar(hacer, mensaje) {
    setOcupado(true)
    try {
      await hacer()
      avisar(mensaje)
      alCambiar()
    } catch (err) {
      avisar(err.message, { tono: 'peligro' })
    } finally {
      setOcupado(false)
    }
  }

  async function terminar() {
    const si = await confirmar({
      titulo: '¿Marcar el trabajo como terminado?',
      mensaje: `${t.cliente.nombre} · ${t.obra.direccion}`,
      confirmarLabel: 'Terminar',
    })
    if (si) ejecutar(() => api.terminarTrabajo(t.id), 'Trabajo terminado.')
  }

  async function cancelar() {
    const si = await confirmar({
      titulo: '¿Cancelar este trabajo?',
      mensaje: `${t.cliente.nombre} en ${t.obra.direccion}. El presupuesto sigue aprobado y se puede volver a pasar a trabajo.`,
      confirmarLabel: 'Cancelar trabajo',
      peligro: true,
    })
    if (si) ejecutar(() => api.cancelarTrabajo(t.id), 'Trabajo cancelado.')
  }

  return (
    <div className="trabajo-detalle">
      <header className="trabajo-encabezado">
        <h2>{t.cliente.nombre}</h2>
        <div className="trabajo-estado">
          <EstadoBadge estado={t.estado} />
          <strong>{textoDeFechas(t)}</strong>
        </div>
      </header>

      <section aria-label="Obra" className="trabajo-bloque">
        <strong>{t.obra.direccion}</strong>
        {t.obra.referencia && <span className="trabajo-sub">{t.obra.referencia}</span>}
        {t.obra.notas && <p className="trabajos-nota">{t.obra.notas}</p>}
        <div className="trabajo-acciones">
          <a className="ui-btn ui-btn--secundario ui-btn--sm" href={urlMapa(t.obra.direccion)} target="_blank" rel="noopener noreferrer">
            <MapPin size={18} aria-hidden="true" /> Cómo llegar
          </a>
          {t.cliente.telefono && (
            <a className="ui-btn ui-btn--secundario ui-btn--sm" href={urlTelefono(t.cliente.telefono)}>
              <Phone size={18} aria-hidden="true" /> {t.cliente.telefono}
            </a>
          )}
        </div>
      </section>

      <section aria-labelledby={`tareas-${t.id}`} className="trabajo-bloque">
        <h3 id={`tareas-${t.id}`}>Tareas</h3>
        <ul className="trabajo-tareas">
          {t.tareas.map((tarea, i) => (
            <li key={i}>
              {tarea.descripcion}
              {tarea.unidad ? ` (${formatoCantidad(tarea.cantidad)} ${tarea.unidad})` : ''}
            </li>
          ))}
        </ul>
        <p className="trabajo-sub">
          {t.plazo_obra ? `Plazo: ${t.plazo_obra} · ` : ''}Materiales: {t.materiales_a_cargo} · Presupuesto Nº {t.presupuesto_numero}
        </p>
      </section>

      <div className="trabajo-acciones">
        {puedeAgendar && (
          <Button variante="primario" icono={CalendarPlus} onClick={() => alElegirDias('agendar')}>
            Agendar
          </Button>
        )}
        {puedeTerminar && (
          <Button variante="primario" icono={SquareCheckBig} disabled={ocupado} onClick={terminar}>
            Terminar
          </Button>
        )}
        {puedeReprogramar && (
          <Button icono={CalendarClock} onClick={() => alElegirDias('reprogramar')}>
            Reprogramar
          </Button>
        )}
        {puedeCancelar && (
          <Button variante="peligro" icono={XCircle} disabled={ocupado} onClick={cancelar}>
            Cancelar trabajo
          </Button>
        )}
      </div>
    </div>
  )
}
