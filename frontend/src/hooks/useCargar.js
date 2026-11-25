import { useCallback, useEffect, useState } from 'react'

/**
 * Pide datos a la API y los mantiene. `recargar()` vuelve a pedirlos SIN mostrar el esqueleto de
 * carga (se conserva lo que ya se ve, para que un cambio no cierre lo que se estaba mirando).
 * `pedir` debe ser estable o venir con `claves` que describan cuándo cambia.
 */
export default function useCargar(pedir, claves = []) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(true)
  const [version, setVersion] = useState(0)

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const pedirEstable = useCallback(pedir, claves)

  useEffect(() => {
    let cancelado = false
    ;(async () => {
      try {
        const resultado = await pedirEstable()
        if (!cancelado) {
          setDatos(resultado)
          setError('')
        }
      } catch (err) {
        if (!cancelado) setError(err.message)
      } finally {
        if (!cancelado) setCargando(false)
      }
    })()
    return () => {
      cancelado = true
    }
  }, [pedirEstable, version])

  const recargar = useCallback(() => setVersion((n) => n + 1), [])
  return { datos, error, cargando, recargar, setDatos }
}
