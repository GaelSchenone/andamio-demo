import { KeyRound, Plus, UserCheck, UserX } from 'lucide-react'
import { useCallback, useState } from 'react'
import { api } from '../../api'
import useCargar from '../../hooks/useCargar'
import { LARGO_MINIMO_PASSWORD, ROLES } from '../../constantes'
import { useSesion } from '../../layout/sesion'
import { Alerta, Avatar, Badge, Button, Input, Modal, Panel, Select, Skeleton, useAvisar, useConfirmar } from '../../ui'
import './Ajustes.css'

const FORM_VACIO = { nombre: '', usuario: '', password: '', rol: 'empleado' }

export default function Usuarios() {
  const { yo } = useSesion()
  const avisar = useAvisar()
  const confirmar = useConfirmar()
  const { datos: usuarios, error, cargando, recargar } = useCargar(useCallback(() => api.listarUsuarios(), []))
  const [creando, setCreando] = useState(false)
  const [claveDe, setClaveDe] = useState(null) // usuario al que se le cambia la contraseña

  async function cambiarDatos(u, cambios, mensaje) {
    try {
      await api.editarUsuario(u.id, cambios)
      avisar(mensaje)
      recargar()
    } catch (err) {
      avisar(err.message, { tono: 'peligro' })
    }
  }

  async function alternarActivo(u) {
    if (u.activo) {
      const si = await confirmar({
        titulo: `¿Desactivar a @${u.usuario}?`,
        mensaje: 'No va a poder entrar a la app hasta que lo reactives. Sus sesiones abiertas se cierran.',
        confirmarLabel: 'Desactivar',
        peligro: true,
      })
      if (!si) return
    }
    cambiarDatos(u, { activo: !u.activo }, u.activo ? `Desactivaste a @${u.usuario}.` : `Reactivaste a @${u.usuario}.`)
  }

  function alternarRol(u) {
    const nuevo = u.rol === 'dueno' ? 'empleado' : 'dueno'
    cambiarDatos(u, { rol: nuevo }, `@${u.usuario} ahora es ${ROLES[nuevo].toLowerCase()}.`)
  }

  return (
    <>
      <p className="ajustes-ayuda">
        Quién puede entrar a la app. El <strong>dueño</strong> puede todo. El <strong>empleado</strong> ve la agenda y los
        clientes y cambia el estado de los trabajos, pero no ve precios ni presupuestos.
      </p>
      <Panel
        titulo="Usuarios"
        acciones={
          <Button variante="primario" tamano="sm" icono={Plus} onClick={() => setCreando(true)}>
            Nuevo usuario
          </Button>
        }
        aria-busy={cargando}
      >
        {error && <Alerta>{error}</Alerta>}
        {cargando && <Skeleton alto="3rem" />}
        {usuarios?.map((u) => {
          const esYo = u.id === yo.id
          return (
            <div className="usuarios-fila" key={u.id}>
              <Avatar nombre={u.nombre} />
              <div className="usuarios-quien">
                <strong>
                  {u.nombre}
                  {esYo ? ' (vos)' : ''}
                </strong>
                <span>@{u.usuario}</span>
              </div>
              <Badge tono={u.rol === 'dueno' ? 'info' : 'neutro'}>{ROLES[u.rol]}</Badge>
              {!u.activo && <Badge tono="peligro" icono={UserX}>Desactivado</Badge>}
              <div className="usuarios-acciones">
                <Button tamano="sm" disabled={esYo} title={esYo ? 'No podés cambiarte el rol a vos mismo' : undefined} onClick={() => alternarRol(u)}>
                  {u.rol === 'dueno' ? 'Pasar a empleado' : 'Pasar a dueño'}
                </Button>
                <Button tamano="sm" icono={KeyRound} onClick={() => setClaveDe(u)}>
                  Contraseña
                </Button>
                <Button
                  tamano="sm"
                  variante={u.activo ? 'peligro' : 'secundario'}
                  icono={u.activo ? UserX : UserCheck}
                  disabled={esYo}
                  title={esYo ? 'No podés desactivarte a vos mismo' : undefined}
                  onClick={() => alternarActivo(u)}
                >
                  {u.activo ? 'Desactivar' : 'Reactivar'}
                </Button>
              </div>
            </div>
          )
        })}
      </Panel>

      <NuevoUsuario
        abierto={creando}
        onCerrar={() => setCreando(false)}
        onCreado={(nuevo) => {
          setCreando(false)
          avisar(`Se creó el usuario @${nuevo.usuario}. Pasale la contraseña en persona.`)
          recargar()
        }}
      />
      <CambiarClave
        usuario={claveDe}
        onCerrar={() => setClaveDe(null)}
        onListo={(u) => {
          setClaveDe(null)
          avisar(`Cambiaste la contraseña de @${u.usuario}. Sus sesiones abiertas se cerraron.`)
        }}
      />
    </>
  )
}

function NuevoUsuario({ abierto, onCerrar, onCreado }) {
  const [form, setForm] = useState(FORM_VACIO)
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const campo = (n) => (e) => setForm((f) => ({ ...f, [n]: e.target.value }))

  async function crear(e) {
    e.preventDefault()
    setError('')
    setEnviando(true)
    try {
      const nuevo = await api.crearUsuario(form)
      setForm(FORM_VACIO)
      onCreado(nuevo)
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Modal
      abierto={abierto}
      onCerrar={onCerrar}
      titulo="Nuevo usuario"
      pie={
        <>
          <Button onClick={onCerrar}>Cancelar</Button>
          <Button type="submit" form="form-nuevo-usuario" variante="primario" cargando={enviando} disabled={!form.nombre.trim() || !form.usuario.trim() || !form.password}>
            Crear usuario
          </Button>
        </>
      }
    >
      <form id="form-nuevo-usuario" className="ajustes-form" onSubmit={crear}>
        <Input etiqueta="Nombre" value={form.nombre} onChange={campo('nombre')} maxLength={100} data-autofocus />
        <Input etiqueta="Usuario" value={form.usuario} onChange={campo('usuario')} autoCapitalize="none" autoCorrect="off" maxLength={40} placeholder="ej: ana" />
        <Select etiqueta="Rol" value={form.rol} onChange={campo('rol')}>
          <option value="empleado">Empleado</option>
          <option value="dueno">Dueño</option>
        </Select>
        <Input
          etiqueta="Contraseña inicial"
          type="password"
          autoComplete="new-password"
          ayuda={`${LARGO_MINIMO_PASSWORD} caracteres o más`}
          value={form.password}
          onChange={campo('password')}
        />
        {error && <Alerta>{error}</Alerta>}
      </form>
    </Modal>
  )
}

function CambiarClave({ usuario, onCerrar, onListo }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function guardar(e) {
    e.preventDefault()
    setError('')
    if (password.length < LARGO_MINIMO_PASSWORD) {
      setError(`La contraseña tiene que tener al menos ${LARGO_MINIMO_PASSWORD} caracteres.`)
      return
    }
    setEnviando(true)
    try {
      await api.restablecerPassword(usuario.id, password)
      setPassword('')
      onListo(usuario)
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Modal
      abierto={Boolean(usuario)}
      onCerrar={onCerrar}
      titulo={`Contraseña de @${usuario?.usuario ?? ''}`}
      pie={
        <>
          <Button onClick={onCerrar}>Cancelar</Button>
          <Button type="submit" form="form-clave-usuario" variante="primario" cargando={enviando} disabled={!password}>
            Guardar contraseña
          </Button>
        </>
      }
    >
      <form id="form-clave-usuario" className="ajustes-form" onSubmit={guardar}>
        <Input
          etiqueta="Contraseña nueva"
          type="password"
          autoComplete="new-password"
          ayuda={`${LARGO_MINIMO_PASSWORD} caracteres o más`}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          data-autofocus
        />
        {error && <Alerta>{error}</Alerta>}
      </form>
    </Modal>
  )
}
