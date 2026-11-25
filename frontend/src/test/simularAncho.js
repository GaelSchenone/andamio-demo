// jsdom no trae matchMedia: este ayudante lo simula para probar el layout por clases de tamaño.
let ancho = 1280
let movimientoReducido = false
const escuchas = new Set()

function evaluar(consulta) {
  if (/prefers-reduced-motion:\s*reduce/.test(consulta)) return movimientoReducido
  const minimo = /min-width:\s*(\d+)px/.exec(consulta)
  return minimo ? ancho >= Number(minimo[1]) : false
}

export function instalarMatchMedia(anchoInicial = 1280, { reducirMovimiento = false } = {}) {
  ancho = anchoInicial
  movimientoReducido = reducirMovimiento
  window.matchMedia = (consulta) => ({
    get matches() {
      return evaluar(consulta)
    },
    media: consulta,
    addEventListener: (_tipo, fn) => escuchas.add(fn),
    removeEventListener: (_tipo, fn) => escuchas.delete(fn),
  })
}

/** Cambia el ancho simulado y avisa a quienes escuchan (como un redimensionado real). */
export function simularAncho(nuevoAncho) {
  ancho = nuevoAncho
  escuchas.forEach((fn) => fn())
}
