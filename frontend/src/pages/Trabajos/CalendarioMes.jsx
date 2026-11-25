import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { api } from '../../api'
import useCargar from '../../hooks/useCargar'
import { INICIALES_DIAS, NOMBRES_MESES, cubreElDia, mesSiguiente, semanaDe, semanasDelMes, sumarDias } from '../../fechas'
import { formatoFecha, hoyISO } from '../../formato'
import { Alerta, Button, EstadoBadge, IconButton } from '../../ui'
import './Calendario.css'

const MAX_POR_CELDA = 2
const NOMBRE_DIA = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

/**
 * Agenda en vista de mes o de semana.
 * - `dia` / `alElegirDia`: el día enfocado (controlado desde afuera; sin ellos, lo maneja el propio calendario).
 * - `trabajoResaltado`: marca en el calendario todos los días que ocupa ese trabajo y lleva la vista hasta él.
 * - `seleccion`: modo "agendar": { trabajoId, dias:Set, despuesDe, alAlternar }. Cada toque marca o desmarca un día; los días que
 *   ya ocupa otro trabajo no se pueden marcar.
 * - `listaDelDia`: si es false, el detalle del día se muestra en otro lado (el panel lateral) y acá no se repite.
 */
export default function CalendarioMes({ modo = 'mes', recarga, trabajoAbierto, alElegirTrabajo, dia: diaPropio, alElegirDia, trabajoResaltado, listaDelDia = true, seleccion }) {
  const hoy = hoyISO()
  const [ancla, setAncla] = useState(hoy) // define el mes o la semana que se ve
  const [diaInterno, setDiaInterno] = useState(hoy)
  const controlado = alElegirDia !== undefined
  const elegido = controlado ? diaPropio : diaInterno
  const mostrado = { anio: Number(ancla.slice(0, 4)), mes: Number(ancla.slice(5, 7)) - 1 }
  const esSemana = modo === 'semana'

  // Al abrir un trabajo, la vista se lleva hasta donde empieza (si no estaba a la vista).
  const inicioResaltado = trabajoResaltado?.fecha_inicio
  const [ultimoResaltado, setUltimoResaltado] = useState(null)
  if (inicioResaltado && trabajoResaltado.id !== ultimoResaltado) {
    setUltimoResaltado(trabajoResaltado.id)
    setAncla(inicioResaltado)
  }
  if (!inicioResaltado && ultimoResaltado !== null) setUltimoResaltado(null)

  const semanas = esSemana ? [semanaDe(ancla)] : semanasDelMes(mostrado.anio, mostrado.mes)
  const desde = semanas[0][0].iso
  const hasta = semanas.at(-1)[6].iso
  const { datos, error } = useCargar(() => api.listarTrabajos({ desde, hasta }), [desde, hasta, recarga])
  const trabajos = datos ?? []

  function elegirDia(iso, delMes) {
    // Tocar el día que ya estaba enfocado lo suelta (vuelve a "todos los trabajos").
    const nuevo = controlado && iso === elegido ? null : iso
    if (controlado) alElegirDia(nuevo)
    else setDiaInterno(iso)
    if (!delMes) setAncla(iso)
  }

  function irAlPeriodo(pasos) {
    if (esSemana) return setAncla(sumarDias(ancla, 7 * pasos))
    const nuevo = mesSiguiente(mostrado, pasos)
    setAncla(`${nuevo.anio}-${String(nuevo.mes + 1).padStart(2, '0')}-01`)
  }

  const titulo = esSemana
    ? `Semana del ${Number(desde.slice(8))} al ${Number(hasta.slice(8))} de ${NOMBRES_MESES[Number(hasta.slice(5, 7)) - 1]}`
    : `${NOMBRES_MESES[mostrado.mes]} ${mostrado.anio}`

  const diaDeLaLista = elegido ?? hoy
  const delDia = trabajos.filter((t) => cubreElDia(t, diaDeLaLista))

  return (
    <div className="calendario">
      <div className="calendario-nav">
        <IconButton icono={ChevronLeft} etiqueta={esSemana ? 'Semana anterior' : 'Mes anterior'} onClick={() => irAlPeriodo(-1)} />
        <h2 className="calendario-titulo" aria-live="polite">
          {titulo}
        </h2>
        <IconButton icono={ChevronRight} etiqueta={esSemana ? 'Semana siguiente' : 'Mes siguiente'} onClick={() => irAlPeriodo(1)} />
        <Button tamano="sm" onClick={() => setAncla(hoy)}>
          Hoy
        </Button>
      </div>

      {error && <Alerta>{error}</Alerta>}

      <div className={`calendario-grilla${esSemana ? ' es-semana' : ''}`} role="group" aria-label={`Calendario: ${titulo}`}>
        {INICIALES_DIAS.map((inicial, i) => (
          <span key={i} className="calendario-dia-semana" aria-hidden="true" title={NOMBRE_DIA[i]}>
            {inicial}
          </span>
        ))}
        {semanas.flat().map((dia) => {
          const deEsteDia = trabajos.filter((t) => cubreElDia(t, dia.iso))
          const ocupadoPorOtro = seleccion && deEsteDia.find((t) => t.id !== seleccion.trabajoId)
          const noElegible = Boolean(ocupadoPorOtro) || Boolean(seleccion?.despuesDe && dia.iso <= seleccion.despuesDe)
          const marcado = Boolean(seleccion?.dias.has(dia.iso))
          const clases = [
            'calendario-celda',
            marcado && 'es-seleccionado',
            seleccion && noElegible && 'es-no-elegible',
            !dia.delMes && 'es-otro-mes',
            dia.finDeSemana && 'es-finde',
            dia.iso === hoy && 'es-hoy',
            !seleccion && dia.iso === elegido && 'es-elegido',
            !seleccion && trabajoResaltado && cubreElDia(trabajoResaltado, dia.iso) && 'es-del-trabajo',
          ]
            .filter(Boolean)
            .join(' ')
          return (
            <button
              key={dia.iso}
              type="button"
              className={clases}
              onClick={() => (seleccion ? !noElegible && seleccion.alAlternar(dia.iso) : elegirDia(dia.iso, dia.delMes))}
              aria-label={`${NOMBRE_DIA[semanas.flat().indexOf(dia) % 7]} ${formatoFecha(dia.iso)}${dia.iso === hoy ? ', hoy' : ''}${marcado ? ', elegido para el trabajo' : ''}${seleccion && ocupadoPorOtro ? `, ocupado por ${ocupadoPorOtro.cliente.nombre}` : ''}: ${deEsteDia.length} ${deEsteDia.length === 1 ? 'trabajo' : 'trabajos'}`}
              aria-pressed={seleccion ? marcado : dia.iso === elegido}
              aria-disabled={seleccion && noElegible ? true : undefined}
            >
              <span className="calendario-numero">{dia.numero}</span>
              <span className="calendario-chips">
                {deEsteDia.slice(0, esSemana ? 99 : MAX_POR_CELDA).map((t) => (
                  <span key={t.id} className={`calendario-chip estado-${t.estado}`}>
                    {t.cliente.nombre}
                  </span>
                ))}
                {!esSemana && deEsteDia.length > MAX_POR_CELDA && <span className="calendario-mas">+{deEsteDia.length - MAX_POR_CELDA}</span>}
              </span>
              {deEsteDia.length > 0 && <span className="calendario-puntos" aria-hidden="true">{'●'.repeat(Math.min(3, deEsteDia.length))}</span>}
            </button>
          )
        })}
      </div>

      {listaDelDia && (
      <section className="calendario-dia" aria-labelledby="titulo-dia">
        <h3 id="titulo-dia">{formatoFecha(diaDeLaLista)}</h3>
        {delDia.length === 0 ? (
          <p className="trabajos-nota">No hay trabajos este día.</p>
        ) : (
          <ul className="calendario-dia-lista">
            {delDia.map((t) => (
              <li key={t.id}>
                <button type="button" aria-current={trabajoAbierto === String(t.id) ? 'true' : undefined} onClick={() => alElegirTrabajo(t)}>
                  <span>
                    <strong>{t.cliente.nombre}</strong>
                    <small>{t.obra.direccion}</small>
                  </span>
                  <EstadoBadge estado={t.estado} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
      )}
    </div>
  )
}
