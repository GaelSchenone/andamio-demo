// Estado compartido de las ventanas abiertas (modal.md: "Let people dismiss a modal view before
// presenting another one"): solo la de arriba reacciona a Escape y a Tab; mientras haya alguna abierta,
// el fondo no se puede scrollear y queda inerte (no recibe foco ni clics, y los lectores de pantalla
// lo ignoran).

const pila = []
let siguiente = 1

/** Registra una ventana nueva y devuelve su identificador. */
export function apilar() {
  const id = siguiente++
  pila.push(id)
  if (pila.length === 1) bloquearFondo()
  return id
}

export function desapilar(id) {
  const posicion = pila.indexOf(id)
  if (posicion === -1) return
  pila.splice(posicion, 1)
  if (pila.length === 0) liberarFondo()
}

export const esLaDeArriba = (id) => pila[pila.length - 1] === id
export const hayVentanasAbiertas = () => pila.length > 0

function bloquearFondo() {
  // Se compensa el ancho de la barra de scroll para que la página no "salte" al abrir una ventana.
  const barra = window.innerWidth - document.documentElement.clientWidth
  document.body.dataset.ventanaAbierta = 'true'
  document.body.style.overflow = 'hidden'
  if (barra > 0) document.body.style.paddingRight = `${barra}px`
  document.getElementById('root')?.setAttribute('inert', '')
}

function liberarFondo() {
  delete document.body.dataset.ventanaAbierta
  document.body.style.overflow = ''
  document.body.style.paddingRight = ''
  document.getElementById('root')?.removeAttribute('inert')
}
