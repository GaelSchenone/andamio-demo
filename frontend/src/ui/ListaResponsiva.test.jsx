import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { instalarMatchMedia, simularAncho } from '../test/simularAncho'
import ListaResponsiva from './ListaResponsiva'

const FILAS = [
  { id: 1, cliente: 'Familia Gómez', direccion: 'Av. Libertador 4500', total: '$ 600.000' },
  { id: 2, cliente: 'Consorcio Sol', direccion: 'Corrientes 1200', total: '$ 1.850.000' },
]

const COLUMNAS = [
  { id: 'cliente', titulo: 'Cliente', celda: (f) => f.cliente, principal: true },
  { id: 'direccion', titulo: 'Dirección', celda: (f) => f.direccion },
  { id: 'total', titulo: 'Total', celda: (f) => f.total, alinear: 'der' },
]

function montar(props = {}) {
  const alElegir = vi.fn()
  render(
    <ListaResponsiva
      nombre="Presupuestos"
      filas={FILAS}
      columnas={COLUMNAS}
      claveDe={(f) => f.id}
      alElegir={alElegir}
      {...props}
    />
  )
  return alElegir
}

beforeEach(() => instalarMatchMedia(1280))

describe('ListaResponsiva en pantalla ancha', () => {
  it('es una tabla con encabezados y una fila por elemento', () => {
    montar()
    const tabla = screen.getByRole('table', { name: 'Presupuestos' })
    expect(within(tabla).getAllByRole('columnheader').map((c) => c.textContent)).toEqual([
      'Cliente',
      'Dirección',
      'Total',
    ])
    expect(within(tabla).getAllByRole('row')).toHaveLength(3) // encabezado + 2
  })

  it('el nombre de cada fila es un botón que la abre', async () => {
    const alElegir = montar()
    await userEvent.click(screen.getByRole('button', { name: 'Consorcio Sol' }))
    expect(alElegir).toHaveBeenCalledWith(FILAS[1])
  })

  it('la fila abierta queda marcada con aria-current (no solo con color)', () => {
    montar({ seleccionada: 2 })
    expect(screen.getByRole('button', { name: 'Consorcio Sol' })).toHaveAttribute('aria-current', 'true')
    expect(screen.getByRole('button', { name: 'Familia Gómez' })).not.toHaveAttribute('aria-current')
  })

  it('se puede usar solo con el teclado', async () => {
    const alElegir = montar()
    await userEvent.tab()
    expect(screen.getByRole('button', { name: 'Familia Gómez' })).toHaveFocus()
    await userEvent.keyboard('{Enter}')
    expect(alElegir).toHaveBeenCalledWith(FILAS[0])
  })
})

describe('ListaResponsiva en celular', () => {
  beforeEach(() => instalarMatchMedia(390))

  it('son tarjetas, no una tabla (nada de scroll horizontal)', () => {
    montar()
    expect(screen.queryByRole('table')).toBeNull()
    const lista = screen.getByRole('list', { name: 'Presupuestos' })
    expect(within(lista).getAllByRole('listitem')).toHaveLength(2)
  })

  it('cada dato lleva su rótulo, y el nombre es el botón que abre la tarjeta', async () => {
    const alElegir = montar()
    const tarjeta = screen.getAllByRole('listitem')[0]
    expect(within(tarjeta).getByText('Dirección')).toBeInTheDocument()
    expect(within(tarjeta).getByText('Av. Libertador 4500')).toBeInTheDocument()
    await userEvent.click(within(tarjeta).getByRole('button', { name: 'Familia Gómez' }))
    expect(alElegir).toHaveBeenCalledWith(FILAS[0])
  })

  it('las columnas marcadas ocultarEnTarjeta no aparecen', () => {
    montar({ columnas: COLUMNAS.map((c) => (c.id === 'total' ? { ...c, ocultarEnTarjeta: true } : c)) })
    expect(screen.queryByText('$ 600.000')).toBeNull()
  })

  it('al agrandar la ventana pasa de tarjetas a tabla sin recargar', () => {
    montar()
    expect(screen.queryByRole('table')).toBeNull()
    act(() => simularAncho(1280))
    expect(screen.getByRole('table')).toBeInTheDocument()
  })
})

describe('etiquetaDe', () => {
  it('permite darle al botón un nombre más completo que el texto visible', () => {
    montar({ etiquetaDe: (f) => `Abrir presupuesto de ${f.cliente}` })
    expect(screen.getByRole('button', { name: 'Abrir presupuesto de Consorcio Sol' })).toBeInTheDocument()
  })
})
