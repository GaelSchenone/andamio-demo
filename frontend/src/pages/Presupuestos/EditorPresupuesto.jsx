import { CircleCheck, Plus } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, ApiError } from '../../api'
import { pesos } from '../../constantes'
import { hoyISO } from '../../formato'
import useSizeClass from '../../hooks/useSizeClass'
import { LARGO_MAXIMO, VIGENCIA_MAXIMA } from '../../limites'
import { animarPasos, crearSeguimiento } from '../../magia'
import CabeceraPagina from '../../layout/CabeceraPagina'
import { coincide, normalizar } from '../../texto'
import { Alerta, Button, Input, Panel, Select, Skeleton, Textarea, useAvisar } from '../../ui'
import ClienteFormulario from '../Clientes/ClienteFormulario'
import ObraFormulario from '../Clientes/ObraFormulario'
import AsistenteIA from './AsistenteIA'
import CampoBuscador from './CampoBuscador'
import ItemEditor from './ItemEditor'
import './Editor.css'

const FORMA_PAGO_DEFAULT = '50% al iniciar y 50% al finalizar'
const MATERIALES_DEFAULT = 'Cliente'
const OBSERVACIONES_DEFAULT =
  'El presupuesto contempla exclusivamente los trabajos detallados anteriormente.\n' +
  'Cualquier trabajo adicional será presupuestado por separado.'

// Orden en que el asistente "escribe" los campos: el mismo en que aparecen en pantalla.
// La IA no completa cliente ni obra: los elige una persona de la lista (así no se cuela uno equivocado).
const CAMPOS_DATOS_IA = ['vigencia_dias', 'plazo_obra']
const CAMPOS_CONDICIONES_IA = ['forma_pago', 'materiales_a_cargo', 'observaciones']
const CAMPOS_ITEM_IA = ['descripcion', 'unidad', 'cantidad', 'importe']

// "items.0.descripcion" -> "descripcion-0" (el id del input en ItemEditor).
function idDeCampo(clave) {
  const [, indice, campo] = clave.split('.')
  return campo ? `${campo}-${indice}` : clave
}

const itemVacio = () => ({ _key: crypto.randomUUID(), descripcion: '', unidad: '', cantidad: '', importe: '' })

const formularioVacio = () => ({
  cliente_obra: '',
  direccion: '',
  fecha_emision: hoyISO(),
  vigencia_dias: 15,
  plazo_obra: '',
  forma_pago: FORMA_PAGO_DEFAULT,
  materiales_a_cargo: MATERIALES_DEFAULT,
  observaciones: OBSERVACIONES_DEFAULT,
  // Opcionales: se eligen de la lista de clientes. Para aprobar el presupuesto hacen falta.
  cliente_id: null,
  obra_id: null,
})

export default function EditorPresupuesto() {
  const { id: editandoId } = useParams()
  const navegar = useNavigate()
  const avisar = useAvisar()
  const clase = useSizeClass()

  const [form, setForm] = useState(formularioVacio)
  const [items, setItems] = useState([itemVacio()])
  const [cargandoInicial, setCargandoInicial] = useState(Boolean(editandoId))
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [creado, setCreado] = useState(null)
  const [iaDisponible, setIaDisponible] = useState(false)
  const [magia, setMagia] = useState(null)
  const [brillos, setBrillos] = useState(() => new Set())
  const [errorIA, setErrorIA] = useState('')
  const [avisoIA, setAvisoIA] = useState('')
  const [campoActivo, setCampoActivo] = useState(null)
  const [clientes, setClientes] = useState([])
  // Las obras se guardan junto con el cliente al que pertenecen, así nunca se ofrecen las de otro.
  const [obras, setObras] = useState({ clienteId: null, lista: [] })
  const opcionesDeObra = obras.clienteId === form.cliente_id ? obras.lista : []
  const [estadoPresupuesto, setEstadoPresupuesto] = useState(null)
  const [teniaVinculo, setTeniaVinculo] = useState(false) // los presupuestos viejos pueden no tener cliente
  const [creandoCliente, setCreandoCliente] = useState(null) // null | texto escrito
  const [creandoObra, setCreandoObra] = useState(null) // null | texto escrito
  const panelIA = useRef(null)
  const seguimiento = useRef(null)

  // Mientras el asistente escribe, la pantalla acompaña al campo que está completando.
  useEffect(() => {
    seguimiento.current ??= crearSeguimiento()
    if (campoActivo) seguimiento.current.mostrar(document.getElementById(idDeCampo(campoActivo)))
  }, [campoActivo])

  useEffect(() => {
    api.estadoAsistente().then((d) => setIaDisponible(d.disponible)).catch(() => setIaDisponible(false))
  }, [])

  useEffect(() => {
    api.listarClientes().then(setClientes).catch(() => setClientes([])) // sin la lista igual se puede escribir a mano
  }, [])

  // Las obras que se ofrecen son las del cliente elegido.
  useEffect(() => {
    const clienteId = form.cliente_id
    if (!clienteId) return undefined
    let cancelado = false
    api
      .obtenerCliente(clienteId)
      .then((c) => !cancelado && setObras({ clienteId, lista: c.obras }))
      .catch(() => !cancelado && setObras({ clienteId, lista: [] }))
    return () => {
      cancelado = true
    }
  }, [form.cliente_id])

  useEffect(() => {
    if (!editandoId) return undefined
    let cancelado = false
    api
      .obtenerPresupuesto(editandoId)
      .then((data) => {
        if (cancelado) return
        setForm({
          cliente_obra: data.cliente_obra,
          direccion: data.direccion,
          fecha_emision: data.fecha_emision,
          vigencia_dias: data.vigencia_dias,
          plazo_obra: data.plazo_obra,
          forma_pago: data.forma_pago,
          materiales_a_cargo: data.materiales_a_cargo,
          observaciones: data.observaciones,
          cliente_id: data.cliente_id,
          obra_id: data.obra_id,
        })
        setEstadoPresupuesto(data.estado)
        setTeniaVinculo(Boolean(data.cliente_id && data.obra_id))
        setItems(
          data.items.map((it) => ({
            _key: String(it.id),
            descripcion: it.descripcion,
            unidad: it.unidad,
            cantidad: String(it.cantidad),
            importe: String(it.importe),
          }))
        )
      })
      .catch(() => setError('No se pudo cargar ese presupuesto.'))
      .finally(() => !cancelado && setCargandoInicial(false))
    return () => {
      cancelado = true
    }
  }, [editandoId])

  const actualizarCampo = (campo, valor) => setForm((f) => ({ ...f, [campo]: valor }))

  // Al elegir un cliente de la lista se copia su nombre al presupuesto (queda como foto del
  // momento: si después cambian los datos del cliente, los PDF ya emitidos no se alteran).
  function elegirCliente(cliente) {
    setForm((f) => ({ ...f, cliente_id: cliente.id, obra_id: null, cliente_obra: cliente.nombre }))
  }

  // Escribir en el campo de cliente suelta el que estaba elegido y su obra: hay que volver a elegir.
  function escribirCliente(texto) {
    setForm((f) => ({ ...f, cliente_obra: texto, cliente_id: null, obra_id: null, direccion: '' }))
  }

  function elegirObra(obra) {
    setForm((f) => ({ ...f, obra_id: obra.id, direccion: obra.direccion }))
  }

  function escribirObra(texto) {
    setForm((f) => ({ ...f, direccion: texto, obra_id: null }))
  }

  // Coincidencias mientras se escribe, sin tildes ni mayúsculas, para no cargar dos veces lo mismo.
  const textoCliente = form.cliente_obra.trim()
  const clientesParecidos = form.cliente_id ? [] : clientes.filter((c) => coincide(c.nombre, textoCliente)).slice(0, 6)
  const clienteYaExiste = clientes.some((c) => normalizar(c.nombre) === normalizar(textoCliente))
  const textoObra = form.direccion.trim()
  const obrasParecidas = form.obra_id ? [] : opcionesDeObra.filter((o) => !textoObra || coincide(`${o.direccion} ${o.referencia}`, textoObra))
  const obraYaExiste = opcionesDeObra.some((o) => normalizar(o.direccion) === normalizar(textoObra))
  const nombreDelCliente = form.cliente_id ? clientes.find((c) => c.id === form.cliente_id)?.nombre : null

  // El cliente recién creado queda elegido; si ya había escrito una dirección, se ofrece guardarla para él.
  function clienteCreado(cliente) {
    setClientes((lista) => [...lista, { ...cliente, cantidad_obras: 0 }])
    elegirCliente(cliente)
    setCreandoCliente(null)
    if (form.direccion.trim()) setCreandoObra(form.direccion.trim())
  }

  function obraCreada(obra) {
    setObras((o) => ({ clienteId: form.cliente_id, lista: o.clienteId === form.cliente_id ? [...o.lista, obra] : [obra] }))
    elegirObra(obra)
    setCreandoObra(null)
  }

  const actualizarItem = (index, campo, valor) => setItems((prev) => prev.map((it, i) => (i === index ? { ...it, [campo]: valor } : it)))

  async function completarConIA(mensaje) {
    setErrorIA('')
    setAvisoIA('')
    setMagia('pensando')
    let borrador
    try {
      borrador = await api.completarConIA(mensaje)
    } catch (err) {
      setMagia(null)
      setErrorIA(err instanceof ApiError ? err.message : 'El asistente no respondió. Probá de nuevo.')
      return
    }

    const conValor = (campo) => borrador[campo] !== null && borrador[campo] !== ''
    const pasoCampo = (campo) => ({ clave: campo, final: borrador[campo], tipear: campo !== 'materiales_a_cargo' })
    const itemsFinal = borrador.items.map((it) => ({
      _key: crypto.randomUUID(),
      descripcion: it.descripcion,
      unidad: it.unidad ?? '',
      cantidad: it.cantidad != null ? String(it.cantidad) : '',
      importe: it.importe != null ? String(it.importe) : '',
    }))
    const pasos = [
      ...CAMPOS_DATOS_IA.filter(conValor).map(pasoCampo),
      ...itemsFinal.flatMap((it, i) =>
        CAMPOS_ITEM_IA.filter((campo) => it[campo] !== '').map((campo) => ({ clave: `items.${i}.${campo}`, final: it[campo] }))
      ),
      ...CAMPOS_CONDICIONES_IA.filter(conValor).map(pasoCampo),
    ]

    if (pasos.length === 0) {
      setMagia(null)
      setErrorIA('No encontré datos para el presupuesto en ese mensaje. Probá con más detalle.')
      return
    }

    const formInicial = form
    const itemsIniciales = items
    setMagia('escribiendo')
    await animarPasos(pasos, (valores) => {
      const formParcial = { ...formInicial }
      for (const campo of [...CAMPOS_DATOS_IA, ...CAMPOS_CONDICIONES_IA]) {
        if (valores.has(campo)) formParcial[campo] = valores.get(campo)
      }
      const itemsVisibles = itemsFinal
        .filter((_, i) => valores.has(`items.${i}.descripcion`))
        .map((it, i) => {
          const parcial = { ...it }
          for (const campo of CAMPOS_ITEM_IA) parcial[campo] = valores.get(`items.${i}.${campo}`) ?? ''
          return parcial
        })
      setForm(formParcial)
      setItems(itemsVisibles.length > 0 ? itemsVisibles : itemsIniciales)
      setBrillos(new Set(valores.keys()))
      setCampoActivo([...valores.keys()].at(-1) ?? null)
    })
    setMagia(null)
    setCampoActivo(null)
    setTimeout(() => setBrillos(new Set()), 1200)
    // Al terminar vuelve al panel, donde está el aviso de qué falta revisar.
    setTimeout(() => seguimiento.current?.mostrar(panelIA.current), 700)

    const sinImporte = itemsFinal.filter((it) => it.importe === '').length
    setAvisoIA(
      sinImporte > 0
        ? `Listo. Revisá los datos y completá ${sinImporte === 1 ? 'el importe que falta' : `los ${sinImporte} importes que faltan`}.`
        : 'Listo. Revisá los datos antes de generar el presupuesto.'
    )
  }

  const brillo = (clave) => (brillos.has(clave) ? 'brillo' : undefined)
  const aprobado = estadoPresupuesto === 'aprobado'
  const total = items.reduce((acc, it) => acc + (Number(it.importe) || 0), 0)

  function validar() {
    if (!form.cliente_obra.trim()) return 'Elegí el cliente (o creá uno nuevo).'
    // Todo presupuesto nuevo lleva cliente y obra de la lista: sin eso no se puede aprobar ni pasar a trabajo.
    if ((!editandoId || teniaVinculo) && (!form.cliente_id || !form.obra_id)) {
      return 'Elegí el cliente y la obra de la lista, o creá los que falten.'
    }
    if (!form.fecha_emision) return 'Ingresá la fecha de emisión.'
    const vigencia = Number(form.vigencia_dias)
    const vigenciaValida = Number.isInteger(vigencia) && vigencia >= 1 && vigencia <= VIGENCIA_MAXIMA
    if (form.vigencia_dias !== '' && !vigenciaValida) {
      return `La vigencia tiene que ser un número entero de días, entre 1 y ${VIGENCIA_MAXIMA}.`
    }
    const camposLargos = [
      ['cliente_obra', 'Cliente / Obra'],
      ['direccion', 'Dirección'],
      ['plazo_obra', 'Plazo de obra'],
      ['forma_pago', 'Forma de pago'],
      ['observaciones', 'Observaciones'],
    ]
    for (const [campo, nombre] of camposLargos) {
      if (form[campo].length > LARGO_MAXIMO[campo]) return `${nombre} tiene más de ${LARGO_MAXIMO[campo]} caracteres. Acortalo un poco.`
    }
    if (items.filter((it) => it.descripcion.trim()).length === 0) return 'Agregá al menos un trabajo con su descripción.'
    for (const [i, it] of items.entries()) {
      if (!it.descripcion.trim()) continue
      if (it.descripcion.trim().length > LARGO_MAXIMO.descripcion) {
        return `La descripción del trabajo ${i + 1} tiene más de ${LARGO_MAXIMO.descripcion} caracteres. Acortala o dividila en dos trabajos.`
      }
      if (it.unidad.trim().length > LARGO_MAXIMO.unidad) return `La unidad del trabajo ${i + 1} tiene más de ${LARGO_MAXIMO.unidad} caracteres.`
      if (!(Number(it.cantidad) > 0)) return `Revisá la cantidad del trabajo "${it.descripcion}".`
      if (!(Number(it.importe) >= 0)) return `Revisá el importe del trabajo "${it.descripcion}".`
    }
    return ''
  }

  async function guardar(e) {
    e.preventDefault()
    const mensajeError = validar()
    if (mensajeError) {
      setError(mensajeError)
      return
    }
    setError('')
    setGuardando(true)
    const payload = {
      ...form,
      vigencia_dias: Number(form.vigencia_dias) || 15,
      items: items
        .filter((it) => it.descripcion.trim())
        .map((it) => ({ descripcion: it.descripcion.trim(), unidad: it.unidad.trim(), cantidad: Number(it.cantidad), importe: Number(it.importe) })),
    }
    try {
      if (editandoId) {
        await api.actualizarPresupuesto(editandoId, payload)
        avisar('Cambios guardados.')
        navegar(`/presupuestos/${editandoId}`)
      } else {
        setCreado(await api.crearPresupuesto(payload))
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar. Probá de nuevo.')
    } finally {
      setGuardando(false)
    }
  }

  function empezarOtro() {
    setForm(formularioVacio())
    setItems([itemVacio()])
    setCreado(null)
    setAvisoIA('')
  }

  if (cargandoInicial) {
    return (
      <div aria-busy="true">
        <Skeleton alto="2rem" ancho="40%" />
      </div>
    )
  }

  if (creado) {
    return (
      <div className="editor-exito">
        <CircleCheck size={48} aria-hidden="true" />
        <h2>Presupuesto Nº {creado.numero} listo</h2>
        <p>
          {creado.cliente_obra} · Total {pesos(creado.total)}
        </p>
        <div className="editor-exito-acciones">
          <a className="ui-btn ui-btn--primario ui-btn--md" href={api.urlPdf(creado.id)} target="_blank" rel="noopener noreferrer">
            Ver / descargar PDF
          </a>
          <Button onClick={empezarOtro}>Crear otro presupuesto</Button>
          <Button onClick={() => navegar(`/presupuestos/${creado.id}`)}>Ir al presupuesto</Button>
        </div>
      </div>
    )
  }

  const ocupadoIA = magia !== null
  const resumen = (
    <div className="editor-total">
      <span>Total</span>
      <strong>{pesos(total)}</strong>
    </div>
  )
  const botonGuardar = (
    <Button type="submit" variante="primario" cargando={guardando} disabled={aprobado}>
      {editandoId ? 'Guardar cambios' : 'Generar presupuesto'}
    </Button>
  )

  return (
    <form onSubmit={guardar} aria-busy={ocupadoIA}>
      <CabeceraPagina
        titulo={editandoId ? 'Editar presupuesto' : 'Nuevo presupuesto'}
        subtitulo={editandoId ? `Nº ${String(editandoId).padStart(4, '0')}` : undefined}
        acciones={<Link className="ui-btn ui-btn--secundario ui-btn--md" to={editandoId ? `/presupuestos/${editandoId}` : '/presupuestos'}>Cancelar</Link>}
      />

      <div className="editor">
        <div className="editor-principal">
          {aprobado && (
            <Alerta>
              Este presupuesto está aprobado y no se puede editar. Para modificarlo, cambiale el estado desde el detalle (si ya tiene un trabajo, primero hay que cancelarlo).
            </Alerta>
          )}

          {iaDisponible && <AsistenteIA panelRef={panelIA} estado={magia} error={errorIA} aviso={avisoIA} onCompletar={completarConIA} />}

          <Panel titulo="Cliente y obra">
            <div className="editor-campos">
              <CampoBuscador
                id="cliente_obra"
                etiqueta="Cliente"
                placeholder="Escribí el nombre para buscarlo"
                maxLength={LARGO_MAXIMO.cliente_obra}
                valor={form.cliente_obra}
                onTexto={escribirCliente}
                elegido={Boolean(form.cliente_id)}
                opciones={clientesParecidos.map((c) => ({
                  id: c.id,
                  titulo: c.nombre,
                  detalle: `${c.cantidad_obras} ${c.cantidad_obras === 1 ? 'obra' : 'obras'}${c.telefono ? ` · ${c.telefono}` : ''}`,
                  elegir: () => elegirCliente(c),
                }))}
                avisoDeCoincidencias="Ya existe un cliente parecido. ¿Es alguno de estos?"
                textoCrear={textoCliente.length >= 2 && !clienteYaExiste ? `Crear “${textoCliente}” como cliente nuevo` : null}
                onCrear={() => setCreandoCliente(textoCliente)}
                ayuda={editandoId && !teniaVinculo ? 'Este presupuesto es viejo y no tiene cliente: elegí uno para poder aprobarlo.' : undefined}
              />
              <CampoBuscador
                id="direccion"
                etiqueta="Obra"
                placeholder={form.cliente_id ? 'Elegí una dirección o escribí una nueva' : 'Primero elegí el cliente'}
                maxLength={LARGO_MAXIMO.direccion}
                valor={form.direccion}
                onTexto={escribirObra}
                deshabilitado={!form.cliente_id}
                elegido={Boolean(form.obra_id)}
                opciones={obrasParecidas.map((o) => ({
                  id: o.id,
                  titulo: o.direccion,
                  detalle: o.referencia || undefined,
                  elegir: () => elegirObra(o),
                }))}
                avisoDeCoincidencias={textoObra ? 'Esa dirección ya existe para este cliente:' : `Direcciones de ${nombreDelCliente}:`}
                textoCrear={form.cliente_id && textoObra.length >= 3 && !obraYaExiste ? `Agregar “${textoObra}” a ${nombreDelCliente}` : null}
                onCrear={() => setCreandoObra(textoObra)}
              />
              <div className="editor-fila">
                <Input id="fecha_emision" etiqueta="Fecha de emisión" type="date" value={form.fecha_emision} onChange={(e) => actualizarCampo('fecha_emision', e.target.value)} />
                <Input id="vigencia_dias" etiqueta="Vigencia (días)" className={brillo('vigencia_dias')} type="number" inputMode="numeric" min="1" max={VIGENCIA_MAXIMA} step="1" value={form.vigencia_dias} onChange={(e) => actualizarCampo('vigencia_dias', e.target.value)} />
              </div>
              <Input id="plazo_obra" etiqueta="Plazo de obra" className={brillo('plazo_obra')} placeholder="Ej: 5 días hábiles" maxLength={LARGO_MAXIMO.plazo_obra} value={form.plazo_obra} onChange={(e) => actualizarCampo('plazo_obra', e.target.value)} />
            </div>
          </Panel>

          <Panel
            titulo="Trabajos a presupuestar"
            acciones={
              <Button tamano="sm" icono={Plus} onClick={() => setItems((prev) => [...prev, itemVacio()])}>
                Agregar trabajo
              </Button>
            }
          >
            <div className="editor-campos">
              <p className="editor-ayuda">Agregá cada tarea con su cantidad y el importe que le vas a cobrar.</p>
              {items.map((item, index) => (
                <ItemEditor
                  key={item._key}
                  item={item}
                  index={index}
                  onChange={(campo, valor) => actualizarItem(index, campo, valor)}
                  onQuitar={() => setItems((prev) => prev.filter((_, i) => i !== index))}
                  puedeQuitar={items.length > 1}
                  brillos={brillos}
                />
              ))}
            </div>
          </Panel>

          <Panel titulo="Condiciones">
            <div className="editor-campos">
              <Input id="forma_pago" etiqueta="Forma de pago" className={brillo('forma_pago')} maxLength={LARGO_MAXIMO.forma_pago} value={form.forma_pago} onChange={(e) => actualizarCampo('forma_pago', e.target.value)} />
              <Select id="materiales_a_cargo" etiqueta="Materiales a cargo de" className={brillo('materiales_a_cargo')} value={form.materiales_a_cargo} onChange={(e) => actualizarCampo('materiales_a_cargo', e.target.value)}>
                <option value="Cliente">Cliente</option>
                <option value="Obras Demo">Obras Demo</option>
                <option value="A convenir">A convenir</option>
              </Select>
              <Textarea id="observaciones" etiqueta="Observaciones" className={brillo('observaciones')} rows={4} maxLength={LARGO_MAXIMO.observaciones} value={form.observaciones} onChange={(e) => actualizarCampo('observaciones', e.target.value)} />
            </div>
          </Panel>

          {error && <Alerta>{error}</Alerta>}
        </div>

        {clase === 'amplia' ? (
          <aside className="editor-lateral" aria-label="Resumen">
            <Panel titulo="Resumen">
              <div className="editor-campos">
                {resumen}
                {botonGuardar}
              </div>
            </Panel>
          </aside>
        ) : (
          <>
            <div className="editor-pie-pagina" aria-hidden="true" />
            <aside className="editor-resumen editor-resumen--fijo" aria-label="Resumen">
              {resumen}
              {botonGuardar}
            </aside>
          </>
        )}
      </div>
      {creandoCliente !== null && (
        <ClienteFormulario abierto nombreInicial={creandoCliente} onCerrar={() => setCreandoCliente(null)} onGuardado={clienteCreado} />
      )}
      {creandoObra !== null && form.cliente_id && (
        <ObraFormulario abierto clienteId={form.cliente_id} direccionInicial={creandoObra} onCerrar={() => setCreandoObra(null)} onGuardado={obraCreada} />
      )}
    </form>
  )
}
