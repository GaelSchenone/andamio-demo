import { useState } from 'react'
import { api } from '../api'
import useSizeClass from '../hooks/useSizeClass'
import Marca from '../layout/Marca'
import { Button, Input } from '../ui'
import './Login.css'

export default function Login({ onIngresar }) {
  const clase = useSizeClass()
  const [usuario, setUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    if (!usuario.trim() || !password) return
    setEnviando(true)
    setError('')
    try {
      onIngresar(await api.login(usuario.trim(), password))
    } catch (err) {
      // El mensaje viene del servidor: "Usuario o contraseña incorrectos." o el aviso de bloqueo.
      setError(err.message)
      setEnviando(false)
    }
  }

  return (
    <div className="login">
      {clase === 'amplia' && (
        <aside className="login-marca" aria-hidden="true">
          <Marca ancho={220} />
          <p>Las obras, los presupuestos y los cobros en un solo lugar.</p>
          <span className="login-cinta" />
        </aside>
      )}
      <main className="login-form-lado">
        <form className="login-form" onSubmit={enviar}>
          {clase !== 'amplia' && <Marca ancho={112} className="login-logo" />}
          <h1>Ingresar</h1>
          <p className="login-sub">Con tu usuario y contraseña.</p>
          <Input
            etiqueta="Usuario"
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            autoFocus
            value={usuario}
            onChange={(e) => setUsuario(e.target.value)}
          />
          <Input
            etiqueta="Contraseña"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={error || undefined}
          />
          <Button type="submit" variante="primario" completo cargando={enviando}>
            Entrar
          </Button>
        </form>
      </main>
    </div>
  )
}
