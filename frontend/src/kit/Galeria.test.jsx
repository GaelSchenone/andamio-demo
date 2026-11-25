import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import { instalarMatchMedia } from '../test/simularAncho'
import Galeria from './Galeria'

beforeEach(() => {
  document.body.innerHTML = ''
  const raiz = document.createElement('div')
  raiz.id = 'root'
  document.body.appendChild(raiz)
  instalarMatchMedia(1280)
})

const montar = () => render(<Galeria />, { container: document.getElementById('root') })

describe('Galería del kit', () => {
  it('se dibuja entera sin errores y muestra todas las secciones', () => {
    montar()
    for (const titulo of ['Botones', 'Campos', 'Ventanas, confirmación y avisos', 'Indicadores']) {
      expect(screen.getByRole('heading', { name: titulo })).toBeInTheDocument()
    }
  })

  it('la ventana de ejemplo se abre y se cierra con Escape', async () => {
    montar()
    await userEvent.click(screen.getByRole('button', { name: 'Abrir ventana' }))
    expect(screen.getByRole('dialog', { name: 'Agendar trabajo' })).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('la confirmación destructiva cancelada avisa que no se eliminó nada', async () => {
    montar()
    await userEvent.click(screen.getByRole('button', { name: 'Pedir confirmación' }))
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(await screen.findByText('No se eliminó nada')).toBeInTheDocument()
  })
})
