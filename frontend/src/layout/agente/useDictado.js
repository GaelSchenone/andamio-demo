import { useCallback, useEffect, useRef, useState } from 'react'

const MENSAJES = {
  'not-allowed': 'No tengo permiso para usar el micrófono. Habilitalo en el navegador.',
  'service-not-allowed': 'Este navegador no permite el dictado por voz.',
  network: 'No se pudo dictar: este navegador no tiene el servicio de voz disponible.',
  'no-speech': 'No te escuché. Probá de nuevo.',
}

/**
 * Dictado por voz con el reconocimiento del navegador (Web Speech API), en español rioplatense.
 * Ojo: Chrome y Edge mandan el audio a su servicio de voz; otros navegadores no lo traen (ahí
 * `soportado` es false y el botón del micrófono no se muestra).
 * `alTexto(texto, esFinal)` recibe lo que va entendiendo.
 */
export default function useDictado(alTexto) {
  const Reconocimiento = typeof window === 'undefined' ? null : window.SpeechRecognition ?? window.webkitSpeechRecognition
  const soportado = Boolean(Reconocimiento)
  const [escuchando, setEscuchando] = useState(false)
  const [error, setError] = useState('')
  const reconocedor = useRef(null)
  const callback = useRef(alTexto)

  useEffect(() => {
    callback.current = alTexto
  })

  useEffect(() => () => reconocedor.current?.abort?.(), [])

  const parar = useCallback(() => reconocedor.current?.stop?.(), [])

  const iniciar = useCallback(() => {
    if (!Reconocimiento) return
    setError('')
    const r = new Reconocimiento()
    r.lang = 'es-AR'
    r.interimResults = true
    r.continuous = false
    r.onresult = (evento) => {
      const resultado = [...evento.results].map((x) => x[0].transcript).join(' ').trim()
      callback.current(resultado, evento.results[evento.results.length - 1].isFinal)
    }
    r.onerror = (evento) => setError(MENSAJES[evento.error] ?? 'No se pudo usar el dictado.')
    r.onend = () => setEscuchando(false)
    reconocedor.current = r
    setEscuchando(true)
    try {
      r.start()
    } catch {
      setEscuchando(false)
    }
  }, [Reconocimiento])

  const alternar = useCallback(() => (escuchando ? parar() : iniciar()), [escuchando, iniciar, parar])

  return { soportado, escuchando, error, alternar }
}
