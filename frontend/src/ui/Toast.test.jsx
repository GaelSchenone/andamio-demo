import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider, useAvisar } from './Toast'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

function Disparador({ mensaje = 'Cliente guardado', opciones }) {
  const avisar = useAvisar()
  return <button onClick={() => avisar(mensaje, opciones)}>Avisar</button>
}

function montar(props) {
  render(
    <ToastProvider>
      <Disparador {...props} />
    </ToastProvider>
  )
}

const avisar = () => fireEvent.click(screen.getByRole('button', { name: 'Avisar' }))

describe('Toast', () => {
  it('la región de avisos existe desde el principio y es aria-live (para que se anuncie)', () => {
    montar()
    const region = screen.getByRole('region', { name: 'Avisos' })
    expect(region).toHaveAttribute('aria-live', 'polite')
  })

  it('un aviso de éxito se muestra como status', () => {
    montar()
    avisar()
    expect(screen.getByRole('status')).toHaveTextContent('Cliente guardado')
  })

  it('el éxito se cierra solo a los 6 segundos', () => {
    montar()
    avisar()
    act(() => vi.advanceTimersByTime(5900))
    expect(screen.getByRole('status')).toBeInTheDocument()
    act(() => vi.advanceTimersByTime(200))
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('un error es un alert y NO desaparece solo', () => {
    montar({ mensaje: 'No se pudo guardar', opciones: { tono: 'peligro' } })
    avisar()
    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo guardar')
    act(() => vi.advanceTimersByTime(60_000))
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('todos tienen un botón para cerrarlos', () => {
    montar({ mensaje: 'No se pudo guardar', opciones: { tono: 'peligro' } })
    avisar()
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar aviso' }))
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('no se acumulan más de 3 avisos', () => {
    montar({ opciones: { tono: 'peligro' } })
    for (let i = 0; i < 6; i++) avisar()
    expect(screen.getAllByRole('alert')).toHaveLength(3)
  })

  it('usar useAvisar sin el proveedor avisa con un error claro', () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Disparador />)).toThrow(/ToastProvider/)
    error.mockRestore()
  })
})
