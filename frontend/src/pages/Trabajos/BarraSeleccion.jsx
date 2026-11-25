import { CalendarCheck } from 'lucide-react'
import { formatoFecha } from '../../formato'
import { Button } from '../../ui'
import './BarraSeleccion.css'

/**
 * Aviso fijo sobre el calendario mientras se eligen los días de un trabajo: dice qué trabajo es,
 * cuántos días hay marcados y deja guardar o cancelar. Los días se marcan tocando el calendario.
 */
export default function BarraSeleccion({ trabajo, modo, dias, guardando, onGuardar, onCancelar }) {
  const orden = [...dias].sort()
  const inicio = orden[0]
  const fin = orden.at(-1)
  return (
    <section className="trabajos-seleccion" aria-label="Elegir los días del trabajo">
      <div className="trabajos-seleccion-cabecera">
        <CalendarCheck size={22} aria-hidden="true" />
        <div>
          <strong>{modo === 'reprogramar' ? 'Reprogramando' : 'Agendando'}: {trabajo.cliente.nombre}</strong>
          <span>{trabajo.obra.direccion}</span>
        </div>
      </div>
      <p className="trabajos-seleccion-resumen" aria-live="polite">
        {orden.length === 0
          ? 'Tocá en el calendario cada día del trabajo (tocalo de nuevo para sacarlo). Los rayados están ocupados.'
          : `${orden.length} ${orden.length === 1 ? 'día elegido' : 'días elegidos'}${orden.length > 1 ? `, del ${formatoFecha(inicio)} al ${formatoFecha(fin)}` : `: ${formatoFecha(inicio)}`}.`}
      </p>
      <div className="trabajos-seleccion-acciones">
        <Button onClick={onCancelar} disabled={guardando}>
          Cancelar
        </Button>
        <Button variante="primario" onClick={onGuardar} cargando={guardando} disabled={orden.length === 0}>
          {modo === 'reprogramar' ? 'Seguir' : 'Guardar días'}
        </Button>
      </div>
    </section>
  )
}
