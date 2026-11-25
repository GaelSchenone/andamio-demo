import { useEffect, useRef } from 'react'
import './Orbe.css'

const PUNTOS = 6

// Cómo se mueve la orbe en cada estado: velocidad de giro, cuánto "habla" (0 a 1), cuánto se abre y
// cierra el anillo (0 a 1) y el tamaño de los puntos.
const ESTADOS = {
  reposo: { velocidad: 0.55, voz: 0, pulso: 0, tamano: 1 },
  pensando: { velocidad: 2.4, voz: 0, pulso: 0, tamano: 1.15 },
  escuchando: { velocidad: 1.1, voz: 0, pulso: 1, tamano: 1 },
  hablando: { velocidad: 0.9, voz: 1, pulso: 0, tamano: 1 },
}

/**
 * Orbe del ayudante: un anillo de puntos que brillan sobre un disco oscuro (dibujada en canvas, sin
 * librerías). `estado` cambia cómo se mueve: "reposo" (lento), "pensando" (rápido), "escuchando"
 * (el anillo se abre y cierra) y "hablando" (cada punto cambia de tamaño y de brillo como una voz).
 * Con "reducir movimiento" se dibuja quieta.
 */
export default function Orbe({ estado = 'reposo', tamano = 56, className = '' }) {
  const lienzo = useRef(null)
  const estadoActual = useRef(estado)

  useEffect(() => {
    estadoActual.current = estado
  }, [estado])

  useEffect(() => {
    const canvas = lienzo.current
    const ctx = canvas?.getContext?.('2d')
    if (!ctx) return undefined
    const estilos = getComputedStyle(canvas)
    const colorPunto = estilos.getPropertyValue('--orbe-punto').trim() || 'white'
    const sinMovimiento = matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const escala = Math.min(window.devicePixelRatio || 1, 2)
    canvas.width = tamano * escala
    canvas.height = tamano * escala
    ctx.scale(escala, escala)

    let fase = 0
    let anterior = performance.now()
    let cuadro = 0
    // Los valores con los que se dibuja se acercan de a poco a los del estado: así pasar de "reposo" a
    // "hablando" (y volver) es un fundido y no un corte. Al callarse baja más lento de lo que sube.
    const actual = { ...ESTADOS.reposo }

    function dibujar(ahora) {
      const dt = Math.min((ahora - anterior) / 1000, 0.05)
      anterior = ahora
      const objetivo = ESTADOS[estadoActual.current] ?? ESTADOS.reposo
      for (const clave of Object.keys(actual)) {
        const ritmo = clave === 'voz' && objetivo.voz < actual.voz ? 2.2 : 5
        actual[clave] += (objetivo[clave] - actual[clave]) * (1 - Math.exp(-dt * ritmo))
      }
      const segundos = ahora / 1000
      fase += dt * actual.velocidad
      ctx.clearRect(0, 0, tamano, tamano)
      const centro = tamano / 2
      const anillo = tamano * (0.2 + 0.05 * Math.sin(fase * 3) * actual.pulso)
      for (let i = 0; i < PUNTOS; i += 1) {
        const angulo = fase + (i * 2 * Math.PI) / PUNTOS
        // Cada punto respira a su ritmo: así el anillo se ve "líquido" y no un reloj.
        const latido = 0.5 + 0.5 * Math.sin(fase * 1.7 + i * 1.9)
        // Al hablar, cada punto sube y baja como las sílabas: dos ondas de distinto ritmo que se multiplican.
        const voz = actual.voz * (0.5 + 0.5 * Math.sin(segundos * 9.1 + i * 1.3) * Math.sin(segundos * 4.3 + 1 + i * 0.7))
        const radio = tamano * (0.045 + 0.03 * latido) * actual.tamano * (1 + 0.9 * voz)
        const x = centro + Math.cos(angulo) * anillo * (1 + 0.12 * Math.sin(fase * 1.3 + i))
        const y = centro + Math.sin(angulo) * anillo * (1 + 0.12 * Math.cos(fase * 1.1 + i))
        ctx.shadowColor = colorPunto
        ctx.shadowBlur = tamano * 0.14 * (1 + 2.4 * voz)
        ctx.fillStyle = colorPunto
        ctx.beginPath()
        ctx.arc(x, y, radio, 0, 2 * Math.PI)
        ctx.fill()
      }
      ctx.shadowBlur = 0
      // El navegador pausa los cuadros con la pestaña oculta. Con "reducir movimiento" queda uno solo.
      if (!sinMovimiento) cuadro = requestAnimationFrame(dibujar)
    }

    cuadro = requestAnimationFrame(dibujar)
    return () => cancelAnimationFrame(cuadro)
  }, [tamano])

  return (
    <span className={`orbe ${className}`.trim()} style={{ width: tamano, height: tamano }} aria-hidden="true">
      <canvas ref={lienzo} style={{ width: tamano, height: tamano }} />
    </span>
  )
}
