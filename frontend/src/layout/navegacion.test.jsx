import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { instalarMatchMedia } from '../test/simularAncho'
import BarraInferior from './BarraInferior'
import BarraLateral from './BarraLateral'
import { BARRA_INFERIOR_POR_ROL, rutasPermitidas } from './navegacion'

const PROHIBIDAS_AL_EMPLEADO = ['/presupuestos', '/cobros']

describe('navegación por rol', () => {
  it('el empleado no tiene Presupuestos ni Cobros en ninguna navegación', () => {
    const rutas = rutasPermitidas('empleado')
    for (const prohibida of PROHIBIDAS_AL_EMPLEADO) expect(rutas).not.toContain(prohibida)
    const { principales, mas } = BARRA_INFERIOR_POR_ROL.empleado
    for (const item of [...principales, ...mas]) expect(PROHIBIDAS_AL_EMPLEADO).not.toContain(item.ruta)
  })

  it('el dueño tiene todas las secciones', () => {
    expect(rutasPermitidas('dueno')).toEqual(expect.arrayContaining(['/', '/trabajos', '/presupuestos', '/cobros', '/clientes', '/ajustes']))
  })

  it('la barra lateral del empleado no muestra enlaces de plata', () => {
    instalarMatchMedia(1280)
    render(<MemoryRouter><BarraLateral rol="empleado" modo="completa" /></MemoryRouter>)
    expect(screen.queryByRole('link', { name: 'Presupuestos' })).toBeNull()
    expect(screen.queryByRole('link', { name: 'Cobros' })).toBeNull()
    expect(screen.getByRole('link', { name: 'Trabajos' })).toBeInTheDocument()
  })

  it('la barra inferior del empleado no tiene "Más" y la del dueño sí', () => {
    instalarMatchMedia(390)
    const { unmount } = render(<MemoryRouter><BarraInferior rol="empleado" /></MemoryRouter>)
    expect(screen.queryByRole('button', { name: 'Más' })).toBeNull()
    unmount()
    render(<MemoryRouter><BarraInferior rol="dueno" /></MemoryRouter>)
    expect(screen.getByRole('button', { name: 'Más' })).toBeInTheDocument()
  })
})
