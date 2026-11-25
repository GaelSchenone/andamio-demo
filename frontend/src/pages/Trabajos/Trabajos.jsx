import { ArrowLeft, HardHat } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import useSizeClass from '../../hooks/useSizeClass'
import { api } from '../../api'
import { ESTADOS_TRABAJO } from '../../estados'
import { textoDeFechas } from '../../constantes'
import { cubreElDia, textoDelDia } from '../../fechas'
import useCargar from '../../hooks/useCargar'
import CabeceraPagina from '../../layout/CabeceraPagina'
import MaestroDetalle from '../../layout/MaestroDetalle'
import { useSesion } from '../../layout/sesion'
import { Alerta, Button, EmptyState, EstadoBadge, ListaResponsiva, Segmentado, Select, Skeleton, useAvisar } from '../../ui'
import BarraSeleccion from './BarraSeleccion'
import CalendarioMes from './CalendarioMes'
import DialogoReprogramar from './DialogoReprogramar'
import TrabajoDetalle from './TrabajoDetalle'
import './Trabajos.css'

// Qué se muestra primero en la lista: lo que está pasando, lo próximo, lo que falta agendar.
const ORDEN = { en_curso: 0, agendado: 1, por_agendar: 2, terminado: 3, cobrado: 4, cancelado: 5 }

const ordenar = (trabajos) =>
  [...trabajos].sort(
    (a, b) =>
      (ORDEN[a.estado] ?? 9) - (ORDEN[b.estado] ?? 9) ||
      (a.fecha_inicio ?? '').localeCompare(b.fecha_inicio ?? '') ||
      b.id - a.id
  )

const COLUMNAS = [
  { id: 'cliente', titulo: 'Cliente', celda: (t) => t.cliente.nombre, principal: true },
  { id: 'obra', titulo: 'Obra', celda: (t) => t.obra.direccion },
  { id: 'fechas', titulo: 'Fechas', celda: (t) => <span className="trabajos-lista-fecha">{textoDeFechas(t)}</span> },
  { id: 'estado', titulo: 'Estado', celda: (t) => <EstadoBadge estado={t.estado} /> },
]

export default function Trabajos() {
  const { esDueno } = useSesion()
  const { id } = useParams()
  const navegar = useNavigate()
  const [params, setParams] = useSearchParams()
  const clase = useSizeClass()
  // El calendario es la vista principal; la lista completa queda como otra vista.
  const vista = ['semana', 'lista'].includes(params.get('vista')) ? params.get('vista') : 'mes'
  const consulta = vista === 'mes' ? '' : `?vista=${vista}`
  const [estado, setEstado] = useState('')
  const [dia, setDia] = useState(null) // día enfocado en el calendario (null = ninguno)
  const avisar = useAvisar()
  // Modo "elegir los días de un trabajo": { trabajo, modo: 'agendar' | 'reprogramar', dias: Set, confirmando }
  const [seleccion, setSeleccion] = useState(null)
  const [guardandoDias, setGuardandoDias] = useState(false)
  // Solo el dueño puede pedir los cancelados; para el empleado no se piden.
  const { datos, error, cargando, recargar } = useCargar(useCallback(() => api.listarTrabajos({ incluirCancelados: esDueno }), [esDueno]), [esDueno])
  const [recargaCalendario, setRecargaCalendario] = useState(0)

  const trabajos = useMemo(() => ordenar(datos ?? []), [datos])
  const activos = trabajos.filter((t) => t.estado !== 'cancelado')
  const visibles = trabajos.filter((t) => (estado ? t.estado === estado : t.estado !== 'cancelado'))
  const abierto = trabajos.find((t) => String(t.id) === id)

  const alCambiar = () => {
    recargar()
    setRecargaCalendario((n) => n + 1)
  }
  const abrir = (t) => navegar(`/trabajos/${t.id}${consulta}`)
  const volver = () => navegar(`/trabajos${consulta}`)

  const consultaCalendario = vista === 'semana' ? '?vista=semana' : ''
  function empezarAElegirDias(t, modo) {
    setSeleccion({ trabajo: t, modo, dias: new Set(modo === 'reprogramar' ? t.dias : []) })
    setDia(null)
    // En pantallas chicas el detalle ocupa toda la pantalla: se pasa al calendario para poder tocar los días.
    navegar(`/trabajos${clase === 'amplia' ? `/${t.id}` : ''}${consultaCalendario}`)
  }

  function terminarDeElegir() {
    const t = seleccion.trabajo
    setSeleccion(null)
    if (clase !== 'amplia') navegar(`/trabajos/${t.id}`)
  }

  function alternarDia(iso) {
    setSeleccion((s) => {
      const dias = new Set(s.dias)
      if (dias.has(iso)) dias.delete(iso)
      else dias.add(iso)
      return { ...s, dias }
    })
  }

  const ordenElegidos = seleccion ? [...seleccion.dias].sort() : []

  async function guardarDias() {
    if (seleccion.modo === 'reprogramar') return setSeleccion((s) => ({ ...s, confirmando: true }))
    setGuardandoDias(true)
    try {
      await api.agendarTrabajo(seleccion.trabajo.id, ordenElegidos)
      avisar('Trabajo agendado.')
      alCambiar()
      terminarDeElegir()
    } catch (err) {
      avisar(err.message, { tono: 'peligro' })
    } finally {
      setGuardandoDias(false)
    }
  }

  const calendarioAncho = vista !== 'lista' && clase === 'amplia'

  // Mientras se eligen los días: en pantallas anchas la barra va al pie del panel de al lado
  // (no agranda la página); en las chicas, abajo del calendario.
  const barraDeSeleccion = seleccion && (
    <BarraSeleccion
      trabajo={seleccion.trabajo}
      modo={seleccion.modo}
      dias={seleccion.dias}
      guardando={guardandoDias}
      onGuardar={guardarDias}
      onCancelar={terminarDeElegir}
    />
  )

  const lista = (
    <div className={`trabajos-pagina${calendarioAncho ? ' trabajos-pagina--fija' : ''}`}>
      <CabeceraPagina
        titulo="Trabajos"
        subtitulo="Lo que está pasando, lo próximo y lo que falta agendar."
        acciones={
          <div className="trabajos-controles">
            {vista === 'lista' && (
              <Select etiqueta="Estado" value={estado} onChange={(e) => setEstado(e.target.value)}>
                <option value="">Todos (sin cancelados)</option>
                {Object.entries(ESTADOS_TRABAJO)
                  .filter(([valor]) => esDueno || valor !== 'cancelado')
                  .map(([valor, etiqueta]) => (
                    <option key={valor} value={valor}>
                      {etiqueta}
                    </option>
                  ))}
              </Select>
            )}
            <Segmentado
              etiqueta="Vista"
              valor={vista}
              onChange={(v) => setParams(v === 'mes' ? {} : { vista: v })}
              opciones={[
                { valor: 'mes', etiqueta: 'Mes' },
                { valor: 'semana', etiqueta: 'Semana' },
                { valor: 'lista', etiqueta: 'Lista' },
              ]}
            />
          </div>
        }
      />
      {error && <Alerta>{error}</Alerta>}
      {vista !== 'lista' ? (
        <CalendarioMes
          modo={vista}
          recarga={recargaCalendario}
          trabajoAbierto={id}
          alElegirTrabajo={abrir}
          dia={dia}
          alElegirDia={(iso) => {
            setDia(iso)
            if (id) volver() // enfocar un día suelta el trabajo abierto
          }}
          trabajoResaltado={abierto}
          listaDelDia={clase !== 'amplia' && !seleccion}
          seleccion={
            seleccion && {
              trabajoId: seleccion.trabajo.id,
              dias: seleccion.dias,
              despuesDe: seleccion.modo === 'reprogramar' && seleccion.trabajo.estado === 'en_curso' ? seleccion.trabajo.fecha_inicio : undefined,
              alAlternar: alternarDia,
            }
          }
        />
      ) : cargando && !datos ? (
        <div aria-busy="true">
          <Skeleton alto="3rem" />
        </div>
      ) : visibles.length === 0 ? (
        <EmptyState
          icono={HardHat}
          titulo={estado ? 'No hay trabajos con ese estado' : 'Todavía no hay trabajos'}
          texto={esDueno ? 'Aprobá un presupuesto y pasalo a trabajo para verlo acá.' : 'Cuando el dueño apruebe un presupuesto, el trabajo va a aparecer acá.'}
        />
      ) : (
        <ListaResponsiva nombre="Trabajos" filas={visibles} columnas={COLUMNAS} claveDe={(t) => String(t.id)} seleccionada={id} alElegir={abrir} />
      )}
      {seleccion && !calendarioAncho && barraDeSeleccion}
    </div>
  )

  // Con el calendario a la vista (pantallas anchas), el panel de al lado muestra todos los trabajos
  // mientras no haya ninguno elegido, y el detalle del elegido cuando lo hay.
  const detalleDeTrabajo = id ? (
    abierto ? (
      <TrabajoDetalle key={abierto.id} trabajo={abierto} alCambiar={alCambiar} alElegirDias={(modo) => empezarAElegirDias(abierto, modo)} />
    ) : datos ? (
      <EmptyState icono={HardHat} titulo="No encontramos ese trabajo" texto="Puede que se haya cancelado o que el enlace sea viejo." />
    ) : (
      <Skeleton alto="6rem" />
    )
  ) : null

  // Tocar cualquier lugar que no sea un día, el panel, los controles del calendario o una ventana
  // (la barra lateral, el fondo de la página…) suelta el día enfocado y el trabajo abierto: el panel
  // vuelve a mostrar todos los trabajos.
  useEffect(() => {
    if (!calendarioAncho || seleccion || (!dia && !id)) return undefined
    const DENTRO = '.calendario-celda, .maestro-detalle-panel, .calendario-nav, .trabajos-controles, [role="dialog"], .ui-modal-fondo, .ui-avisos'
    function alTocar(evento) {
      if (evento.target.closest?.(DENTRO)) return
      // Un enlace a otra sección (Cobros, Clientes…) tiene que llevar ahí: no lo pisamos con un navegar a /trabajos.
      const enlace = evento.target.closest?.('a[href]')
      if (enlace && !enlace.pathname.startsWith('/trabajos')) return
      setDia(null)
      if (id) navegar(`/trabajos${consulta}`)
    }
    document.addEventListener('click', alTocar)
    return () => document.removeEventListener('click', alTocar)
  }, [calendarioAncho, seleccion, dia, id, consulta, navegar])

  const delDia = dia ? activos.filter((t) => cubreElDia(t, dia)) : []

  const contenidoDelPanel = calendarioAncho ? (
    id ? (
      <div className="trabajos-detalle-lateral">
        <Button variante="fantasma" tamano="sm" icono={ArrowLeft} onClick={volver}>
          {dia ? textoDelDia(dia) : 'Todos los trabajos'}
        </Button>
        {detalleDeTrabajo}
      </div>
    ) : dia ? (
      <ListaLateral
        titulo={textoDelDia(dia)}
        trabajos={delDia}
        cargando={cargando && !datos}
        alElegir={abrir}
        vacio="No hay trabajos este día."
        accion={
          <Button variante="fantasma" tamano="sm" onClick={() => setDia(null)}>
            Ver todos los trabajos
          </Button>
        }
      />
    ) : (
      <ListaLateral titulo="Todos los trabajos" trabajos={activos} cargando={cargando && !datos} alElegir={abrir} />
    )
  ) : (
    detalleDeTrabajo
  )
  const detalle = calendarioAncho && seleccion ? (
    <div className="trabajos-panel-con-barra">
      <div className="trabajos-panel-contenido">{contenidoDelPanel}</div>
      {barraDeSeleccion}
    </div>
  ) : (
    contenidoDelPanel
  )

  return (
    <>
    {seleccion?.confirmando && (
      <DialogoReprogramar
        trabajo={seleccion.trabajo}
        dias={ordenElegidos}
        onCerrar={() => setSeleccion((s) => ({ ...s, confirmando: false }))}
        onHecho={(mensaje) => {
          avisar(mensaje)
          alCambiar()
          terminarDeElegir()
        }}
      />
    )}
    <MaestroDetalle
      lista={lista}
      detalle={detalle}
      alVolver={volver}
      fijo={calendarioAncho}
      etiquetaVolver="Trabajos"
      vacio={{ icono: HardHat, titulo: 'Elegí un trabajo', texto: 'Ves la obra, las tareas y lo que podés hacer acá.' }}
    />
    </>
  )
}

function ListaLateral({ titulo, trabajos, cargando, alElegir, vacio = 'Todavía no hay trabajos', accion }) {
  return (
    <section aria-labelledby="titulo-lateral" className="trabajos-lateral">
      <h2 id="titulo-lateral">{titulo}</h2>
      {accion}
      {cargando ? (
        <Skeleton alto="4rem" />
      ) : trabajos.length === 0 ? (
        <EmptyState icono={HardHat} titulo={vacio} />
      ) : (
        <ul>
          {trabajos.map((t) => (
            <li key={t.id}>
              <button type="button" onClick={() => alElegir(t)}>
                <span>
                  <strong>{t.cliente.nombre}</strong>
                  <small>
                    {t.obra.direccion} · {textoDeFechas(t)}
                  </small>
                </span>
                <EstadoBadge estado={t.estado} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
