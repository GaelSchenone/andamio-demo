import { useState } from 'react'
import { api } from '../../api'
import { LARGO_MINIMO_PASSWORD, ROLES } from '../../constantes'
import { useSesion } from '../../layout/sesion'
import { Alerta, Avatar, Badge, Button, Input, Panel } from '../../ui'
import './Ajustes.css'

export default function MiCuenta() {
  const { yo } = useSesion()
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [repetida, setRepetida] = useState('')
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function cambiar(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    if (nueva.length < LARGO_MINIMO_PASSWORD) {
      setError(`La contraseña nueva tiene que tener al menos ${LARGO_MINIMO_PASSWORD} caracteres.`)
      return
    }
    if (nueva !== repetida) {
      setError('Las contraseñas nuevas no coinciden.')
      return
    }
    setEnviando(true)
    try {
      await api.cambiarPassword(actual, nueva)
      setActual('')
      setNueva('')
      setRepetida('')
      setAviso('Listo, cambiaste tu contraseña. Las demás sesiones abiertas se cerraron.')
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <>
      <Panel>
        <div className="ajustes-datos">
          <Avatar nombre={yo.nombre} tamano={56} />
          <div>
            <strong>{yo.nombre}</strong>
            <p>@{yo.usuario}</p>
          </div>
          <Badge tono={yo.rol === 'dueno' ? 'info' : 'neutro'}>{ROLES[yo.rol]}</Badge>
        </div>
      </Panel>

      <Panel titulo="Cambiar contraseña">
        <form className="ajustes-form" onSubmit={cambiar}>
          <Input etiqueta="Contraseña actual" type="password" autoComplete="current-password" value={actual} onChange={(e) => setActual(e.target.value)} />
          <Input
            etiqueta="Contraseña nueva"
            type="password"
            autoComplete="new-password"
            ayuda={`${LARGO_MINIMO_PASSWORD} caracteres o más`}
            value={nueva}
            onChange={(e) => setNueva(e.target.value)}
          />
          <Input etiqueta="Repetí la contraseña nueva" type="password" autoComplete="new-password" value={repetida} onChange={(e) => setRepetida(e.target.value)} />
          {error && <Alerta>{error}</Alerta>}
          {aviso && <Alerta tono="ok">{aviso}</Alerta>}
          <div>
            <Button type="submit" variante="primario" cargando={enviando} disabled={!actual || !nueva || !repetida}>
              Cambiar contraseña
            </Button>
          </div>
        </form>
      </Panel>
    </>
  )
}
