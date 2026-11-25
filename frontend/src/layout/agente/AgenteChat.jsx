import { Mic, MicOff, RotateCcw, SendHorizontal, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api'
import useSizeClass from '../../hooks/useSizeClass'
import { Alerta, Button, IconButton } from '../../ui'
import { useSesion } from '../sesion'
import './AgenteChat.css'
import Orbe from './Orbe'
import Texto from './Texto'
import Pensando from './Pensando'
import useDictado from './useDictado'
import useMaquinaDeEscribir, { recortar } from './useMaquinaDeEscribir'

const SUGERENCIAS = {
  dueno: ['¿Qué trabajos tengo esta semana?', '¿Cuánto me deben en total?', '¿Cómo agendo un trabajo?'],
  empleado: ['¿Qué trabajos tengo hoy?', '¿Cómo inicio un trabajo?', '¿Dónde queda el próximo trabajo?'],
}
const MAX_ENVIADOS = 20

/**
 * El ayudante: una orbe flotante que abre un chat con el agente. El agente solo consulta y guía: cuando
 * hay que ir a una pantalla muestra un botón. Si el servidor no tiene Gemini configurado, no aparece nada.
 */
export default function AgenteChat() {
  const { yo } = useSesion()
  const navegar = useNavigate()
  const clase = useSizeClass()
  const [disponible, setDisponible] = useState(false)
  const [simulado, setSimulado] = useState(false) // versión de demostración: respuestas por reglas
  const [abierto, setAbierto] = useState(false)
  const [mensajes, setMensajes] = useState([])
  const [entrada, setEntrada] = useState('')
  const [pensando, setPensando] = useState(false)
  const [error, setError] = useState('')
  const [conversacionId, setConversacionId] = useState(null)
  const [escribiendo, setEscribiendo] = useState(null) // posición del mensaje que se está "tipeando"
  const lista = useRef(null)
  const orbe = useRef(null)
  const campo = useRef(null)
  const fin = useRef(null)

  useEffect(() => {
    api
      .estadoAgente()
      .then((d) => {
        setDisponible(d.disponible)
        setSimulado(Boolean(d.simulado))
      })
      .catch(() => setDisponible(false))
  }, [])

  const dictado = useDictado((texto) => setEntrada(texto))

  useEffect(() => {
    if (abierto) campo.current?.focus()
  }, [abierto])

  useEffect(() => {
    fin.current?.scrollIntoView?.({ block: 'end' })
  }, [mensajes, pensando])

  useEffect(() => {
    if (!abierto) return undefined
    const alTeclear = (e) => e.key === 'Escape' && cerrar()
    document.addEventListener('keydown', alTeclear)
    return () => document.removeEventListener('keydown', alTeclear)
  })

  if (!disponible) return null

  function cerrar() {
    setAbierto(false)
    orbe.current?.focus()
  }

  async function enviar(texto = entrada) {
    const limpio = texto.trim()
    if (!limpio || pensando) return
    if (dictado.escuchando) dictado.alternar()
    const nuevos = [...mensajes, { rol: 'usuario', texto: limpio }]
    setMensajes(nuevos)
    setEntrada('')
    setError('')
    setPensando(true)
    try {
      const r = await api.chatAgente(nuevos.slice(-MAX_ENVIADOS).map(({ rol, texto: t }) => ({ rol, texto: t })), conversacionId)
      setMensajes([...nuevos, { rol: 'agente', texto: r.respuesta, acciones: r.acciones }])
      // La respuesta llega entera; se muestra tipeada, salvo que la persona pidiera menos movimiento.
      if (!matchMedia('(prefers-reduced-motion: reduce)').matches) setEscribiendo(nuevos.length)
      setConversacionId(r.conversacion_id ?? null)
    } catch (err) {
      setError(err.message)
    } finally {
      setPensando(false)
    }
  }

  function ir(ruta) {
    navegar(ruta)
    if (clase === 'compacta') cerrar()
  }

  const estadoOrbe = pensando ? 'pensando' : escribiendo !== null ? 'hablando' : dictado.escuchando ? 'escuchando' : 'reposo'
  const alAvanzar = () => lista.current && (lista.current.scrollTop = lista.current.scrollHeight)

  return (
    <div className="agente" data-abierto={abierto}>
      {/* El chat siempre está montado: la orbe y la caja son el mismo objeto, que se expande y se encoge.
          La caja es la superficie que crece; el contenido va adentro, anclado a la esquina, y se revela. */}
      <div className="agente-caja">
      <section id="agente-panel" className="agente-panel" role="dialog" aria-label="Asistente de Andamio" aria-hidden={!abierto} inert={!abierto}>
        <header className="agente-cabecera">
          <div>
            <h2>Asistente</h2>
            {simulado && <p className="agente-simulado">Modo demo: respuestas simuladas</p>}
          </div>
          {mensajes.length > 0 && (
            <IconButton icono={RotateCcw} etiqueta="Empezar una conversación nueva" onClick={() => { setMensajes([]); setError(''); setConversacionId(null) }} />
          )}
          <IconButton icono={X} etiqueta="Cerrar el asistente" onClick={cerrar} />
        </header>

          <div ref={lista} className="agente-mensajes" role="log" aria-live="polite" aria-busy={pensando}>
            {mensajes.length === 0 && (
              <div className="agente-inicio">
                <p>Hola, {yo.nombre.split(' ')[0]}. ¿En qué te ayudo?</p>
                <ul>
                  {SUGERENCIAS[yo.rol].map((s) => (
                    <li key={s}>
                      <button type="button" onClick={() => enviar(s)}>
                        {s}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {mensajes.map((m, i) => (
              <div key={i} className={`agente-mensaje agente-mensaje--${m.rol}`}>
                <span className="sr-only">{m.rol === 'usuario' ? 'Vos: ' : 'Asistente: '}</span>
                {m.rol === 'usuario' && <p>{m.texto}</p>}
                {m.rol === 'agente' && i === escribiendo && (
                  <Tipeando texto={m.texto} alAvanzar={alAvanzar} alTerminar={() => setEscribiendo(null)} />
                )}
                {m.rol === 'agente' && i !== escribiendo && <Texto texto={m.texto} />}
                {m.acciones?.length > 0 && i !== escribiendo && (
                  <div className="agente-acciones">
                    {m.acciones.map((a) => (
                      <Button key={a.ruta} tamano="sm" onClick={() => ir(a.ruta)}>
                        {a.etiqueta}
                      </Button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {pensando && <Pensando />}
            {error && <Alerta>{error}</Alerta>}
            <div ref={fin} />
          </div>

          {dictado.error && <Alerta tono="info" className="agente-aviso">{dictado.error}</Alerta>}
          <form
            className="agente-entrada"
            onSubmit={(e) => {
              e.preventDefault()
              enviar()
            }}
          >
            <label className="sr-only" htmlFor="agente-texto">
              Escribile al asistente
            </label>
            <textarea
              id="agente-texto"
              ref={campo}
              rows={1}
              value={entrada}
              maxLength={1500}
              placeholder={dictado.escuchando ? 'Te estoy escuchando…' : 'Escribí tu pregunta…'}
              onChange={(e) => setEntrada(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  enviar()
                }
              }}
            />
            {dictado.soportado && (
              <IconButton
                icono={dictado.escuchando ? MicOff : Mic}
                etiqueta={dictado.escuchando ? 'Dejar de dictar' : 'Dictar con la voz'}
                aria-pressed={dictado.escuchando}
                onClick={dictado.alternar}
              />
            )}
            <IconButton icono={SendHorizontal} etiqueta="Enviar" type="submit" disabled={!entrada.trim() || pensando} />
          </form>
      </section>
      </div>

      <button
        ref={orbe}
        type="button"
        className="agente-orbe"
        aria-label={abierto ? 'Cerrar el asistente' : 'Abrir el asistente'}
        aria-expanded={abierto}
        aria-controls="agente-panel"
        onClick={() => (abierto ? cerrar() : setAbierto(true))}
      >
        <Orbe estado={estadoOrbe} tamano={56} />
      </button>
    </div>
  )
}

// La respuesta de a poco, como si se escribiera. Tocar el mensaje la muestra entera. Los lectores de
// pantalla reciben el texto completo de una vez (no cada letra) y la parte visible no se lee.
function Tipeando({ texto, alAvanzar, alTerminar }) {
  const cuantos = useMaquinaDeEscribir(texto, { alAvanzar, alTerminar })
  return (
    <div className="agente-tipeando" onClick={alTerminar} title="Tocá para ver todo el mensaje">
      <span className="sr-only">{texto}</span>
      <div aria-hidden="true">
        <Texto texto={recortar(texto, cuantos)} />
      </div>
    </div>
  )
}
