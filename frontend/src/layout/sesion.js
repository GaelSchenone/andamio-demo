import { createContext, useContext } from 'react'

export const SesionContexto = createContext(null)

/** El usuario que entró: { id, nombre, usuario, rol }, y `esDueno`. */
export function useSesion() {
  const sesion = useContext(SesionContexto)
  if (!sesion) throw new Error('useSesion necesita estar dentro de <SesionContexto.Provider>.')
  return sesion
}
