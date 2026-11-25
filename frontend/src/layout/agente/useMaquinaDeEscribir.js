import { useEffect, useRef, useState } from 'react'

const MINIMO_CARACTERES_POR_SEGUNDO = 90
const DURACION_MAXIMA_S = 4

/**
 * El texto hasta el carácter `n`, sin dejar el formato a medias: si queda una negrita abierta ("**do")
 * se la cierra, y un "*" suelto al final (la mitad de "**") se oculta. Así no parpadean los asteriscos.
 */
export function recortar(texto, n) {
  let recorte = texto.slice(0, n)
  if (recorte.endsWith('*') && !recorte.endsWith('**') && texto[n] === '*') recorte = recorte.slice(0, -1)
  if (((recorte.match(/\*\*/g) ?? []).length) % 2 === 1) recorte += '**'
  return recorte
}

/**
 * Efecto de máquina de escribir: devuelve cuántos caracteres de `texto` mostrar, creciendo cuadro a
 * cuadro. Va a 90 caracteres por segundo o más rápido si el texto es largo, para no tardar más de unos 4 s.
 * Cuando termina llama a `alTerminar`; `alAvanzar` se llama en cada cuadro (para acompañar con el scroll).
 */
export default function useMaquinaDeEscribir(texto, { alAvanzar, alTerminar }) {
  const [cuantos, setCuantos] = useState(0)
  const callbacks = useRef({ alAvanzar, alTerminar })

  useEffect(() => {
    callbacks.current = { alAvanzar, alTerminar }
  })

  useEffect(() => {
    const velocidad = Math.max(MINIMO_CARACTERES_POR_SEGUNDO, texto.length / DURACION_MAXIMA_S)
    let inicio = null
    let cuadro = 0
    function paso(ahora) {
      inicio ??= ahora
      const n = Math.min(texto.length, Math.floor(((ahora - inicio) / 1000) * velocidad))
      setCuantos(n)
      callbacks.current.alAvanzar?.()
      if (n >= texto.length) callbacks.current.alTerminar?.()
      else cuadro = requestAnimationFrame(paso)
    }
    cuadro = requestAnimationFrame(paso)
    return () => cancelAnimationFrame(cuadro)
  }, [texto])

  return cuantos
}
