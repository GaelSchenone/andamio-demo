import { useSyncExternalStore } from 'react'

// Clases de tamaño: el layout se decide por el espacio disponible, no por el tipo de aparato
// (layout.md › Size classes). Los cortes coinciden con los de los estilos (720 y 1024 px).
export const CORTE_MEDIA = 720
export const CORTE_AMPLIA = 1024

const consultaMedia = `(min-width: ${CORTE_MEDIA}px)`
const consultaAmplia = `(min-width: ${CORTE_AMPLIA}px)`

function suscribir(avisar) {
  const listas = [matchMedia(consultaMedia), matchMedia(consultaAmplia)]
  listas.forEach((lista) => lista.addEventListener('change', avisar))
  return () => listas.forEach((lista) => lista.removeEventListener('change', avisar))
}

function leer() {
  if (typeof matchMedia === 'undefined') return 'amplia'
  if (matchMedia(consultaAmplia).matches) return 'amplia'
  if (matchMedia(consultaMedia).matches) return 'media'
  return 'compacta'
}

/** 'compacta' (< 720 px) | 'media' (720-1023) | 'amplia' (≥ 1024). Se actualiza al redimensionar. */
export default function useSizeClass() {
  return useSyncExternalStore(suscribir, leer, () => 'amplia')
}
