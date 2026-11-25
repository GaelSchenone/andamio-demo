import { CalendarClock, CalendarDays, HardHat, SquareCheckBig, Wallet } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api'
import { pesos, textoDeFechas } from '../../constantes'
import { NOMBRES_MESES, cubreElDia, sumarDias } from '../../fechas'
import { hoyISO } from '../../formato'
import useCargar from '../../hooks/useCargar'
import { useSesion } from '../../layout/sesion'
import { Alerta, Button, EmptyState, EstadoBadge, Kpi, Panel, Skeleton, useAvisar, useConfirmar } from '../../ui'
import CalendarioMes from '../Trabajos/CalendarioMes'
import './Inicio.css'

const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado']

function saludo(hoy) {
  const [a, m, d] = hoy.split('-').map(Number)
  const fecha = new Date(a, m - 1, d)
  return `${DIAS[fecha.getDay()]} ${d} de ${NOMBRES_MESES[m - 1]}`
}

const ACTIVOS = ['agendado', 'en_curso']

export default function Inicio() {
  const { yo, esDueno } = useSesion()
  const navegar = useNavigate()
  const avisar = useAvisar()
  const confirmar = useConfirmar()
  const hoy = hoyISO()
  const finSemana = sumarDias(hoy, 6)
  const [recarga, setRecarga] = useState(0)

  const trabajosQ = useCargar(useCallback(() => api.listarTrabajos(), []))
  const cobrosQ = useCargar(useCallback(() => (esDueno ? api.cobrosPendientes() : Promise.resolve(null)), [esDueno]), [esDueno])

  const { deHoy, deLaSemana, porAgendar } = useMemo(() => {
    const todos = trabajosQ.datos ?? []
    const activos = todos.filter((t) => ACTIVOS.includes(t.estado) && t.fecha_inicio)
    const entre = (t) => t.dias.some((d) => d >= hoy && d <= finSemana)
    return {
      deHoy: activos.filter((t) => cubreElDia(t, hoy)),
      deLaSemana: activos.filter(entre).sort((a, b) => a.fecha_inicio.localeCompare(b.fecha_inicio)),
      porAgendar: todos.filter((t) => t.estado === 'por_agendar'),
    }
  }, [trabajosQ.datos, hoy, finSemana])

  async function accion(t, hacer, mensaje) {
    try {
      await hacer()
      avisar(mensaje)
      trabajosQ.recargar()
      setRecarga((n) => n + 1)
    } catch (err) {
      avisar(err.message, { tono: 'peligro' })
    }
  }

  async function terminar(t) {
    const si = await confirmar({
      titulo: '¿Marcar el trabajo como terminado?',
      mensaje: `${t.cliente.nombre} · ${t.obra.direccion}`,
      confirmarLabel: 'Terminar',
    })
    if (si) accion(t, () => api.terminarTrabajo(t.id), 'Trabajo terminado.')
  }

  const nombre = yo.nombre.split(' ')[0]
  const cobros = cobrosQ.datos

  return (
    <>
      <header className="inicio-saludo">
        <h1>Hola, {nombre}</h1>
        <p>{saludo(hoy)}</p>
      </header>

      {(trabajosQ.error || cobrosQ.error) && <Alerta>{trabajosQ.error || cobrosQ.error}</Alerta>}

      <div className="inicio-kpis" aria-busy={trabajosQ.cargando}>
        <Kpi etiqueta="Hoy" valor={trabajosQ.datos ? deHoy.length : '—'} icono={HardHat} ayuda={deHoy.length === 1 ? 'trabajo' : 'trabajos'} onClick={() => navegar('/trabajos?vista=semana')} />
        <Kpi etiqueta="Esta semana" valor={trabajosQ.datos ? deLaSemana.length : '—'} icono={CalendarDays} ayuda="próximos 7 días" onClick={() => navegar('/trabajos')} />
        <Kpi etiqueta="Por agendar" valor={trabajosQ.datos ? porAgendar.length : '—'} icono={CalendarClock} onClick={() => navegar('/trabajos')} />
        {esDueno && <Kpi etiqueta="Falta cobrar" valor={cobros ? pesos(cobros.total_pendiente) : '—'} icono={Wallet} onClick={() => navegar('/cobros')} />}
      </div>

      <div className={`inicio-columnas${esDueno ? '' : ' inicio-columnas--una'}`}>
        <div className="inicio-principal">
          <Panel titulo="Hoy y esta semana" icono={HardHat} aria-busy={trabajosQ.cargando}>
            {!trabajosQ.datos ? (
              <Skeleton alto="4rem" />
            ) : deLaSemana.length === 0 ? (
              <EmptyState icono={CalendarDays} titulo="No hay trabajos en los próximos 7 días" texto={esDueno ? 'Agendá los que están por agendar.' : 'Cuando agenden uno, lo ves acá.'} />
            ) : (
              <ul className="inicio-trabajos">
                {deLaSemana.map((t) => (
                  <li key={t.id}>
                    <div className="inicio-trabajo-datos">
                      <Link to={`/trabajos/${t.id}`}>
                        <strong>{t.cliente.nombre}</strong>
                      </Link>
                      <span>
                        {t.obra.direccion} · {textoDeFechas(t)}
                      </span>
                    </div>
                    <EstadoBadge estado={t.estado} />
                    <div className="inicio-trabajo-acciones">
                      <Button tamano="sm" icono={SquareCheckBig} onClick={() => terminar(t)}>
                        Terminar
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel titulo="Calendario" icono={CalendarDays}>
            <CalendarioMes recarga={recarga} alElegirTrabajo={(t) => navegar(`/trabajos/${t.id}`)} />
          </Panel>
        </div>

        {esDueno && (
          <div className="inicio-lateral">
            <Panel titulo="Falta cobrar" icono={Wallet} aria-busy={!cobros}>
              {!cobros ? (
                <Skeleton alto="4rem" />
              ) : cobros.trabajos.length === 0 ? (
                <EmptyState icono={Wallet} titulo="No hay nada pendiente" texto="Los trabajos con saldo por cobrar aparecen acá." />
              ) : (
                <ul className="inicio-cobros">
                  {cobros.trabajos.slice(0, 6).map((t) => (
                    <li key={t.trabajo_id}>
                      <Link to={`/cobros/${t.trabajo_id}`}>
                        <span>
                          <strong>{t.cliente}</strong>
                          <small>{t.direccion}</small>
                        </span>
                        <strong className="inicio-cobro-monto">{pesos(t.pendiente)}</strong>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
        )}
      </div>
    </>
  )
}
