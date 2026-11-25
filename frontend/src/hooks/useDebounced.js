import { useEffect, useState } from 'react'

/** Devuelve `valor` recién cuando dejó de cambiar durante `demora` ms (para buscadores). */
export default function useDebounced(valor, demora = 300) {
  const [retrasado, setRetrasado] = useState(valor)
  useEffect(() => {
    const temporizador = setTimeout(() => setRetrasado(valor), demora)
    return () => clearTimeout(temporizador)
  }, [valor, demora])
  return retrasado
}
