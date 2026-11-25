// Reglas de diseño que se pueden comprobar sin mirar la pantalla: contraste de la paleta, que los
// colores vivan solo en tokens.css y que ningún texto baje del tamaño mínimo.
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

// Se leen los archivos desde el disco: con `css: false`, Vitest devuelve los .css vacíos al importarlos,
// y las comprobaciones pasarían "en falso" sin revisar nada.
const SRC = join(process.cwd(), 'src') // Vitest corre desde frontend/
const leer = (ruta) => readFileSync(join(SRC, ruta), 'utf8')
const tokens = leer('styles/tokens.css')

const EXCLUIDOS = ['styles/tokens.css']
const estilos = readdirSync(SRC, { recursive: true })
  .map((ruta) => String(ruta).replaceAll('\\', '/'))
  .filter((ruta) => ruta.endsWith('.css') && !EXCLUIDOS.includes(ruta))
  .map((ruta) => [ruta, leer(ruta)])

function leerColores(texto) {
  const colores = {}
  for (const [, nombre, valor] of texto.matchAll(/--([\w-]+):\s*(#[0-9a-f]{6})\s*;/gi)) {
    colores[nombre] = valor
  }
  return colores
}

const corteOscuro = tokens.indexOf('@media (prefers-color-scheme: dark)')
const corteContraste = tokens.indexOf('@media (prefers-contrast: more)')
const claro = leerColores(tokens.slice(0, corteOscuro))
const oscuro = { ...claro, ...leerColores(tokens.slice(corteOscuro, corteContraste)) }

function luminancia(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
  const lineal = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  return 0.2126 * lineal(r) + 0.7152 * lineal(g) + 0.0722 * lineal(b)
}

function contraste(a, b) {
  const [alto, bajo] = [luminancia(a), luminancia(b)].sort((x, y) => y - x)
  return (alto + 0.05) / (bajo + 0.05)
}

const sinComentarios = (css) => css.replace(/\/\*[\s\S]*?\*\//g, '')

describe.each([
  ['claro', claro],
  ['oscuro', oscuro],
])('paleta en modo %s', (_nombre, c) => {
  it('el texto se lee sobre cada superficie (4.5:1)', () => {
    for (const texto of ['text', 'text-2', 'text-3']) {
      for (const fondo of ['bg', 'surface']) {
        expect(contraste(c[texto], c[fondo]), `${texto} sobre ${fondo}`).toBeGreaterThanOrEqual(4.5)
      }
    }
    // El texto terciario también se usa sobre superficies hundidas (chips, filas con hover).
    expect(contraste(c['text-3'], c['surface-2'])).toBeGreaterThanOrEqual(4.5)
    expect(contraste(c['text-2'], c['surface-2'])).toBeGreaterThanOrEqual(4.5)
  })

  it('el botón primario (texto oscuro sobre el acento) se lee (4.5:1)', () => {
    expect(contraste(c['on-accent'], c.accent)).toBeGreaterThanOrEqual(4.5)
  })

  it('el botón destructivo sólido (texto del fondo sobre el rojo) se lee (4.5:1)', () => {
    expect(contraste(c.bg, c.bad)).toBeGreaterThanOrEqual(4.5)
  })

  it('el borde de los controles se distingue de la superficie (3:1)', () => {
    expect(contraste(c['border-strong'], c.surface)).toBeGreaterThanOrEqual(3)
  })

  it.each(['ok', 'warn', 'bad', 'info'])('el estado "%s" se lee sobre su fondo suave (4.5:1)', (estado) => {
    expect(contraste(c[estado], c[`${estado}-bg`])).toBeGreaterThanOrEqual(4.5)
  })
})

describe('disciplina de estilos', () => {
  it('de verdad se están leyendo los archivos (guarda contra pasar en falso)', () => {
    expect(tokens.length).toBeGreaterThan(1500)
    expect(Object.keys(claro).length).toBeGreaterThan(15)
    expect(estilos.map(([ruta]) => ruta)).toContain('styles/base.css')
    for (const [ruta, css] of estilos) expect(css.length, ruta).toBeGreaterThan(0)
  })

  it('ningún .css fuera de tokens.css escribe colores sueltos', () => {
    const infractores = []
    for (const [ruta, css] of estilos) {
      const limpio = sinComentarios(css)
      if (/#[0-9a-f]{3,8}\b/i.test(limpio) || /\b(?:rgba?|hsla?|oklch|oklab)\(/i.test(limpio)) {
        infractores.push(ruta)
      }
    }
    expect(infractores, 'usar var(--...) de tokens.css').toEqual([])
  })

  it('ningún texto es más chico que 12 px', () => {
    const chicos = []
    for (const [ruta, css] of estilos) {
      for (const [, numero, unidad] of sinComentarios(css).matchAll(/font-size:\s*([\d.]+)(px|rem|em)/g)) {
        const px = unidad === 'px' ? Number(numero) : Number(numero) * 16
        if (px < 12) chicos.push(`${ruta}: ${numero}${unidad}`)
      }
    }
    expect(chicos).toEqual([])
  })

  it('tokens.css declara el tamaño mínimo y el objetivo táctil de las guías', () => {
    expect(tokens).toMatch(/--fs-xs:\s*0\.75rem/)
    expect(tokens).toMatch(/--hit:\s*44px/)
  })
})
