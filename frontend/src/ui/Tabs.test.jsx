import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import Tabs from './Tabs'

const PESTANAS = [
  { id: 'cuenta', etiqueta: 'Mi cuenta' },
  { id: 'usuarios', etiqueta: 'Usuarios' },
  { id: 'otra', etiqueta: 'Otra' },
]

function Ejemplo() {
  const [activa, setActiva] = useState('cuenta')
  return <Tabs pestanas={PESTANAS} activa={activa} onChange={setActiva} etiqueta="Ajustes" />
}

describe('Tabs', () => {
  it('usa los roles de WAI-ARIA y marca la activa', () => {
    render(<Ejemplo />)
    expect(screen.getByRole('tablist', { name: 'Ajustes' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Mi cuenta' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Usuarios' })).toHaveAttribute('aria-selected', 'false')
  })

  it('cada pestaña apunta a su panel', () => {
    render(<Ejemplo />)
    expect(screen.getByRole('tab', { name: 'Usuarios' })).toHaveAttribute('aria-controls', 'panel-usuarios')
  })

  it('solo la pestaña activa entra en el orden de Tab', () => {
    render(<Ejemplo />)
    expect(screen.getByRole('tab', { name: 'Mi cuenta' })).toHaveAttribute('tabindex', '0')
    expect(screen.getByRole('tab', { name: 'Usuarios' })).toHaveAttribute('tabindex', '-1')
  })

  it('las flechas cambian de pestaña y mueven el foco; dan la vuelta en los extremos', async () => {
    render(<Ejemplo />)
    screen.getByRole('tab', { name: 'Mi cuenta' }).focus()
    await userEvent.keyboard('{ArrowRight}')
    expect(screen.getByRole('tab', { name: 'Usuarios' })).toHaveFocus()
    expect(screen.getByRole('tab', { name: 'Usuarios' })).toHaveAttribute('aria-selected', 'true')
    await userEvent.keyboard('{ArrowRight}{ArrowRight}')
    expect(screen.getByRole('tab', { name: 'Mi cuenta' })).toHaveFocus()
    await userEvent.keyboard('{ArrowLeft}')
    expect(screen.getByRole('tab', { name: 'Otra' })).toHaveFocus()
  })

  it('Inicio y Fin saltan a la primera y a la última', async () => {
    render(<Ejemplo />)
    screen.getByRole('tab', { name: 'Mi cuenta' }).focus()
    await userEvent.keyboard('{End}')
    expect(screen.getByRole('tab', { name: 'Otra' })).toHaveFocus()
    await userEvent.keyboard('{Home}')
    expect(screen.getByRole('tab', { name: 'Mi cuenta' })).toHaveFocus()
  })

  it('un clic también cambia de pestaña', async () => {
    render(<Ejemplo />)
    await userEvent.click(screen.getByRole('tab', { name: 'Otra' }))
    expect(screen.getByRole('tab', { name: 'Otra' })).toHaveAttribute('aria-selected', 'true')
  })
})
