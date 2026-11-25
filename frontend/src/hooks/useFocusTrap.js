// Foco dentro de las ventanas: entra al abrir, no se escapa con Tab y vuelve a donde estaba al cerrar.

const FOCUSABLES = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

export function elementosEnfocables(contenedor) {
  return [...contenedor.querySelectorAll(FOCUSABLES)].filter((el) => !el.hasAttribute('inert'))
}

/** Foco inicial: lo marcado con data-autofocus; si no, el primer campo del cuerpo; si no, la ventana. */
export function enfocarAlAbrir(ventana, cuerpo) {
  const marcado = ventana.querySelector('[data-autofocus]')
  const primero = marcado ?? (cuerpo ? elementosEnfocables(cuerpo)[0] : undefined)
  ;(primero ?? ventana).focus()
}

/** Mantiene Tab y Mayús+Tab dentro de la ventana. Devuelve true si manejó la tecla. */
export function atraparTab(evento, ventana) {
  if (evento.key !== 'Tab') return false
  const lista = elementosEnfocables(ventana)
  if (lista.length === 0) {
    evento.preventDefault()
    ventana.focus()
    return true
  }
  const primero = lista[0]
  const ultimo = lista[lista.length - 1]
  const activo = document.activeElement
  if (!ventana.contains(activo)) {
    evento.preventDefault()
    primero.focus()
  } else if (evento.shiftKey && activo === primero) {
    evento.preventDefault()
    ultimo.focus()
  } else if (!evento.shiftKey && activo === ultimo) {
    evento.preventDefault()
    primero.focus()
  } else {
    return false
  }
  return true
}
