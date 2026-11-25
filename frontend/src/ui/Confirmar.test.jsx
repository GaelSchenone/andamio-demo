import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ConfirmarProvider, useConfirmar } from './Confirmar'

beforeEach(() => {
  document.body.innerHTML = ''
  const raiz = document.createElement('div')
  raiz.id = 'root'
  document.body.appendChild(raiz)
})

function Prueba({ opciones, alResponder }) {
  const confirmar = useConfirmar()
  return <button onClick={async () => alResponder(await confirmar(opciones))}>Borrar</button>
}

function montar(opciones = { titulo: '¿Eliminar el cliente?', mensaje: 'No se puede deshacer.' }) {
  const alResponder = vi.fn()
  render(
    <ConfirmarProvider>
      <Prueba opciones={opciones} alResponder={alResponder} />
    </ConfirmarProvider>,
    { container: document.getElementById('root') }
  )
  return alResponder
}

describe('Confirmar (reemplaza a window.confirm)', () => {
  it('muestra un diálogo con el título y el mensaje', async () => {
    montar()
    await userEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    const dialogo = screen.getByRole('dialog', { name: '¿Eliminar el cliente?' })
    expect(dialogo).toHaveAccessibleDescription('No se puede deshacer.')
  })

  it('el foco arranca en Cancelar, no en la acción destructiva', async () => {
    montar({ titulo: 'T', confirmarLabel: 'Eliminar', peligro: true })
    await userEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus()
  })

  it('un Enter apenas aparece el diálogo cancela (no confirma por accidente)', async () => {
    const alResponder = montar({ titulo: 'T', confirmarLabel: 'Eliminar', peligro: true })
    await userEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    await userEvent.keyboard('{Enter}')
    expect(alResponder).toHaveBeenCalledWith(false)
  })

  it('Confirmar devuelve true', async () => {
    const alResponder = montar({ titulo: 'T', confirmarLabel: 'Eliminar' })
    await userEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }))
    expect(alResponder).toHaveBeenCalledWith(true)
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it.each([
    ['Cancelar', () => userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))],
    ['Escape', () => userEvent.keyboard('{Escape}')],
    ['el botón Cerrar', () => userEvent.click(screen.getByRole('button', { name: 'Cerrar' }))],
    ['tocar afuera', () => userEvent.click(document.querySelector('.ui-modal-fondo'))],
  ])('%s devuelve false', async (_nombre, accion) => {
    const alResponder = montar({ titulo: 'T', confirmarLabel: 'Eliminar' })
    await userEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    await accion()
    expect(alResponder).toHaveBeenCalledWith(false)
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('la acción destructiva lleva el estilo de peligro; la normal, el primario', async () => {
    montar({ titulo: 'T', confirmarLabel: 'Eliminar', peligro: true })
    await userEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    expect(screen.getByRole('button', { name: 'Eliminar' })).toHaveClass('ui-btn--peligro-solido')
  })

  it('usar useConfirmar sin el proveedor avisa con un error claro', () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Prueba opciones={{}} alResponder={() => {}} />)).toThrow(/ConfirmarProvider/)
    error.mockRestore()
  })
})
