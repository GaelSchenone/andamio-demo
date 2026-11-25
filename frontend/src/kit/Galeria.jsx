import {
  CalendarDays,
  HardHat,
  Phone,
  Plus,
  Search,
  Trash2,
  Users,
  Wallet,
} from 'lucide-react'
import { useState } from 'react'
import {
  Avatar,
  Badge,
  Button,
  ConfirmarProvider,
  EmptyState,
  EstadoBadge,
  IconButton,
  Input,
  Kpi,
  ListaResponsiva,
  Modal,
  Panel,
  SearchField,
  Segmentado,
  Select,
  Skeleton,
  Tabs,
  Textarea,
  ToastProvider,
  useAvisar,
  useConfirmar,
} from '../ui'
import useSizeClass from '../hooks/useSizeClass'
import './Galeria.css'

const COLORES = [
  ['--bg', 'Fondo'],
  ['--surface', 'Superficie'],
  ['--surface-2', 'Hundida'],
  ['--border-strong', 'Borde de control'],
  ['--text', 'Texto'],
  ['--text-2', 'Texto 2'],
  ['--text-3', 'Texto 3'],
  ['--accent', 'Acento (cinta)'],
  ['--ok', 'Éxito'],
  ['--warn', 'Alerta'],
  ['--bad', 'Peligro'],
  ['--info', 'Info'],
]

const FILAS = [
  { id: 1, cliente: 'Consorcio Los Álamos', direccion: 'Corrientes 1200', estado: 'en_curso', total: '$ 1.850.000' },
  { id: 2, cliente: 'Familia Gómez', direccion: 'Av. Libertador 4500', estado: 'agendado', total: '$ 600.000' },
  { id: 3, cliente: 'Marta Pérez', direccion: 'Calle Falsa 123', estado: 'terminado', total: '$ 276.000' },
]

const COLUMNAS = [
  { id: 'cliente', titulo: 'Cliente', celda: (f) => f.cliente, principal: true },
  { id: 'direccion', titulo: 'Dirección', celda: (f) => f.direccion },
  { id: 'estado', titulo: 'Estado', celda: (f) => <EstadoBadge estado={f.estado} /> },
  { id: 'total', titulo: 'Total', celda: (f) => f.total, alinear: 'der' },
]

function Seccion({ titulo, children }) {
  return (
    <section className="kit-seccion">
      <h2>{titulo}</h2>
      {children}
    </section>
  )
}

function Demo() {
  const avisar = useAvisar()
  const confirmar = useConfirmar()
  const clase = useSizeClass()
  const [vista, setVista] = useState('lista')
  const [pestana, setPestana] = useState('cuenta')
  const [busqueda, setBusqueda] = useState('')
  const [ventana, setVentana] = useState(false)
  const [elegida, setElegida] = useState(1)

  async function pedirConfirmacion() {
    const si = await confirmar({
      titulo: '¿Eliminar el cliente?',
      mensaje: 'Se borran sus datos y no se puede deshacer.',
      confirmarLabel: 'Eliminar',
      peligro: true,
    })
    avisar(si ? 'Cliente eliminado' : 'No se eliminó nada', { tono: si ? 'ok' : 'peligro' })
  }

  return (
    <main className="kit">
      <header className="kit-cabecera">
        <h1>Kit de componentes</h1>
        <p>
          Clase de tamaño actual: <strong>{clase}</strong>. Cambiá el ancho de la ventana para ver la lista pasar de tabla a
          tarjetas, y el modo claro/oscuro del sistema para ver los dos temas.
        </p>
      </header>

      <Seccion titulo="Colores (todos salen de tokens.css)">
        <div className="kit-colores">
          {COLORES.map(([variable, nombre]) => (
            <div key={variable} className="kit-color">
              <span className="kit-muestra" style={{ background: `var(${variable})` }} />
              <span>{nombre}</span>
              <code>{variable}</code>
            </div>
          ))}
        </div>
      </Seccion>

      <Seccion titulo="Tipografía">
        <p className="kit-display">Hola, Dora</p>
        <p className="kit-kpi-demo">$ 4.413.000</p>
        <p>
          Cuerpo en Inter 16 px: Los trabajos de hoy son dos. Corrientes 1200, hall y escaleras, y Libertador 4500.
        </p>
        <p className="kit-chico">Texto chico (12 px): referencia, notas y rótulos de datos.</p>
      </Seccion>

      <Seccion titulo="Botones">
        <div className="kit-fila">
          <Button variante="primario" icono={Plus}>Nuevo presupuesto</Button>
          <Button>Secundario</Button>
          <Button variante="fantasma">Fantasma</Button>
          <Button variante="peligro" icono={Trash2}>Eliminar</Button>
          <Button variante="peligro-solido">Eliminar ya</Button>
          <Button variante="primario" cargando>Guardando</Button>
          <Button disabled>Desactivado</Button>
          <Button tamano="sm">Chico</Button>
          <IconButton icono={Phone} etiqueta="Llamar" />
        </div>
      </Seccion>

      <Seccion titulo="Estados (ícono + texto + color: nunca solo color)">
        <div className="kit-fila">
          {['por_agendar', 'agendado', 'en_curso', 'terminado', 'cobrado', 'cancelado'].map((e) => (
            <EstadoBadge key={e} estado={e} />
          ))}
        </div>
        <div className="kit-fila">
          {['borrador', 'enviado', 'aprobado', 'rechazado'].map((e) => (
            <EstadoBadge key={e} tipo="presupuesto" estado={e} />
          ))}
          <Badge icono={Users}>Casa</Badge>
        </div>
      </Seccion>

      <Seccion titulo="Indicadores">
        <div className="kit-grilla">
          <Kpi etiqueta="Hoy" valor="2" icono={HardHat} ayuda="trabajos" />
          <Kpi etiqueta="Esta semana" valor="5" icono={CalendarDays} />
          <Kpi etiqueta="Por agendar" valor="1" onClick={() => avisar('Iría a Trabajos, filtrado')} />
          <Kpi etiqueta="Falta cobrar" valor="$ 4.413.000" icono={Wallet} />
        </div>
      </Seccion>

      <Seccion titulo="Campos">
        <div className="kit-grilla kit-grilla--campos">
          <Input etiqueta="Nombre" placeholder="Nombre y apellido" />
          <Input etiqueta="Teléfono" ayuda="Con código de área" opcional />
          <Input etiqueta="Usuario" error="Solo letras sin tildes, números, punto y guion" defaultValue="Ana López" />
          <Select etiqueta="Tipo" defaultValue="casa">
            <option value="casa">Casa</option>
            <option value="consorcio">Consorcio</option>
          </Select>
          <Textarea etiqueta="Notas" opcional placeholder="Ej: prefiere que lo llamen de tarde" />
          <SearchField etiqueta="Buscar clientes" valor={busqueda} onChange={setBusqueda} placeholder="Buscar por nombre o dirección…" />
        </div>
      </Seccion>

      <Seccion titulo="Navegación interna">
        <div className="kit-fila">
          <Segmentado
            etiqueta="Vista"
            valor={vista}
            onChange={setVista}
            opciones={[
              { valor: 'lista', etiqueta: 'Lista' },
              { valor: 'calendario', etiqueta: 'Calendario' },
            ]}
          />
        </div>
        <Tabs
          etiqueta="Ajustes"
          activa={pestana}
          onChange={setPestana}
          pestanas={[
            { id: 'cuenta', etiqueta: 'Mi cuenta' },
            { id: 'usuarios', etiqueta: 'Usuarios' },
          ]}
        />
      </Seccion>

      <Seccion titulo="Panel y lista responsiva (tabla ≥ 720 px, tarjetas en celular)">
        <Panel titulo="Presupuestos" icono={Search} acciones={<Button tamano="sm" icono={Plus}>Nuevo</Button>}>
          <ListaResponsiva
            nombre="Presupuestos de ejemplo"
            filas={FILAS}
            columnas={COLUMNAS}
            claveDe={(f) => f.id}
            seleccionada={elegida}
            alElegir={(f) => setElegida(f.id)}
          />
        </Panel>
      </Seccion>

      <Seccion titulo="Cargando y vacío">
        <div className="kit-grilla">
          <Panel titulo="Cargando" aria-busy="true">
            <div className="kit-pila">
              <Skeleton alto="1.25rem" ancho="60%" />
              <Skeleton alto="1rem" />
              <Skeleton alto="1rem" ancho="80%" />
            </div>
          </Panel>
          <Panel titulo="Sin datos">
            <EmptyState
              icono={CalendarDays}
              titulo="No hay trabajos este día"
              texto="Cuando agendes uno, va a aparecer acá."
              accion={<Button tamano="sm">Ver todos</Button>}
            />
          </Panel>
        </div>
      </Seccion>

      <Seccion titulo="Ventanas, confirmación y avisos">
        <div className="kit-fila">
          <Button onClick={() => setVentana(true)}>Abrir ventana</Button>
          <Button variante="peligro" onClick={pedirConfirmacion}>Pedir confirmación</Button>
          <Button onClick={() => avisar('Cliente guardado')}>Aviso de éxito</Button>
          <Button onClick={() => avisar('No se pudo guardar. Revisá tu conexión.', { tono: 'peligro' })}>
            Aviso de error
          </Button>
        </div>
        <p className="kit-chico">
          La ventana es un diálogo centrado desde 720 px y una hoja que sube desde abajo en celular (con manija para
          deslizar). Probá Escape, Tab, y tocar afuera.
        </p>
      </Seccion>

      <Modal
        abierto={ventana}
        onCerrar={() => setVentana(false)}
        titulo="Agendar trabajo"
        descripcion="Elegí desde qué día hasta qué día se hace."
        pie={
          <>
            <Button onClick={() => setVentana(false)}>Cancelar</Button>
            <Button variante="primario" onClick={() => setVentana(false)}>Guardar fechas</Button>
          </>
        }
      >
        <div className="kit-grilla kit-grilla--campos">
          <Input etiqueta="Desde" type="date" />
          <Input etiqueta="Hasta (inclusive)" type="date" />
        </div>
        <div className="kit-fila">
          <Avatar nombre="Dora" />
          <span className="kit-chico">Lo agenda el dueño; la empleada solo inicia y termina.</span>
        </div>
      </Modal>
    </main>
  )
}

export default function Galeria() {
  return (
    <ToastProvider>
      <ConfirmarProvider>
        <Demo />
      </ConfirmarProvider>
    </ToastProvider>
  )
}
