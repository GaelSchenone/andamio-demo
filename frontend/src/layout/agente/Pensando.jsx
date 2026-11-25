import { useEffect, useState } from 'react'

// Verbos de "estoy pensando", mitad serios y mitad bichos, para que la espera no sea siempre la misma palabra.
export const FRASES = [
  'Pensando…',
  'Cavilando…',
  'Razonando…',
  'Reflexionando…',
  'Analizando…',
  'Elucubrando…',
  'Rumiando…',
  'Meditando…',
  'Maquinando…',
  'Ponderando…',
  'Deliberando…',
  'Conjeturando…',
  'Procesando…',
  'Sintetizando…',
  'Destilando ideas…',
  'Hilando fino…',
  'Atando cabos…',
  'Barajando opciones…',
  'Dándole vueltas…',
  'Cocinando una respuesta…',
  'Fermentando ideas…',
  'Conectando puntos…',
  'Tramando…',
  'Discurriendo…',
  'Cogitando…',
  'Contemplando…',
  'Escarbando datos…',
  'Haciendo cuentas…',
]

const CADA_MS = 2600
const MUESTRA_EL_TIEMPO_DESDE_S = 5

/** Una frase al azar distinta de la anterior. */
export const otraFrase = (anterior) => {
  const i = Math.floor(Math.random() * (FRASES.length - 1))
  return i >= anterior ? i + 1 : i
}

/**
 * Indicador de "pensando" mientras llega la respuesta: un puntito que late, una frase al azar que brilla y
 * cambia cada pocos segundos, y los segundos que lleva esperando (a partir de los 5). Los lectores de
 * pantalla oyen solo "Pensando…" una vez, no cada frase.
 */
export default function Pensando() {
  const [frase, setFrase] = useState(() => Math.floor(Math.random() * FRASES.length))
  const [segundos, setSegundos] = useState(0)

  useEffect(() => {
    const inicio = Date.now()
    const cambiar = setInterval(() => setFrase(otraFrase), CADA_MS)
    const contar = setInterval(() => setSegundos(Math.floor((Date.now() - inicio) / 1000)), 1000)
    return () => {
      clearInterval(cambiar)
      clearInterval(contar)
    }
  }, [])

  return (
    <p className="agente-pensando" role="status">
      <span className="sr-only">Pensando…</span>
      <span className="agente-pensando-punto" aria-hidden="true" />
      <span key={frase} className="agente-pensando-frase" aria-hidden="true">
        {FRASES[frase]}
      </span>
      {segundos >= MUESTRA_EL_TIEMPO_DESDE_S && (
        <span className="agente-pensando-tiempo" aria-hidden="true">
          {segundos} s
        </span>
      )}
    </p>
  )
}
