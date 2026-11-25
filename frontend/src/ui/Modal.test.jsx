import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Modal from './Modal'

let raiz
beforeEach(() => {
  document.body.innerHTML = ''
  raiz = document.createElement('div')
  raiz.id = 'root'
  document.body.appendChild(raiz)
  Element.prototype.setPointerCapture = vi.fn()
})

const mostrar = (ui) => render(ui, { container: raiz })

function Ejemplo(props) {
  const [abierto, setAbierto] = useState(false)
  return (
    <>
      <button onClick={() => setAbierto(true)}>Abrir</button>
      <Modal abierto={abierto} onCerrar={() => setAbierto(false)} titulo="Agendar trabajo" {...props}>
        <input aria-label="Desde" />
        <input aria-label="Hasta" />
      </Modal>
    </>
  )
}

describe('Modal', () => {
  it('cerrada no dibuja nada', () => {
    mostrar(<Modal abierto={false} onCerrar={() => {}} titulo="X" />)
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('es un diálogo modal con el título como nombre accesible', () => {
    mostrar(<Modal abierto onCerrar={() => {}} titulo="Agendar trabajo" descripcion="Elegí las fechas" />)
    const dialogo = screen.getByRole('dialog', { name: 'Agendar trabajo' })
    expect(dialogo).toHaveAttribute('aria-modal', 'true')
    expect(dialogo).toHaveAccessibleDescription('Elegí las fechas')
  })

  it('el foco entra al primer campo (no al botón de cerrar)', () => {
    mostrar(<Modal abierto onCerrar={() => {}} titulo="X"><input aria-label="Desde" /></Modal>)
    expect(screen.getByLabelText('Desde')).toHaveFocus()
  })

  it('el foco entra a lo marcado con data-autofocus', () => {
    mostrar(
      <Modal abierto onCerrar={() => {}} titulo="X">
        <input aria-label="Desde" />
        <button data-autofocus>Cancelar</button>
      </Modal>
    )
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus()
  })

  it('si no hay nada enfocable, el foco queda en la ventana', () => {
    mostrar(<Modal abierto onCerrar={() => {}} titulo="X">Solo texto</Modal>)
    // el botón de cerrar está en la cabecera, no en el cuerpo: igual el foco tiene que estar adentro
    expect(screen.getByRole('dialog')).toContainElement(document.activeElement)
  })

  it('Escape la cierra', async () => {
    const onCerrar = vi.fn()
    mostrar(<Modal abierto onCerrar={onCerrar} titulo="X" />)
    await userEvent.keyboard('{Escape}')
    expect(onCerrar).toHaveBeenCalledTimes(1)
  })

  it('el botón Cerrar tiene nombre accesible y la cierra', async () => {
    const onCerrar = vi.fn()
    mostrar(<Modal abierto onCerrar={onCerrar} titulo="X" />)
    await userEvent.click(screen.getByRole('button', { name: 'Cerrar' }))
    expect(onCerrar).toHaveBeenCalledTimes(1)
  })

  it('Tab nunca saca el foco de la ventana, en ninguna dirección', async () => {
    mostrar(
      <Modal abierto onCerrar={() => {}} titulo="X" pie={<button>Guardar</button>}>
        <input aria-label="Desde" />
      </Modal>
    )
    const dialogo = screen.getByRole('dialog')
    for (let i = 0; i < 8; i++) {
      await userEvent.tab()
      expect(dialogo).toContainElement(document.activeElement)
    }
    for (let i = 0; i < 8; i++) {
      await userEvent.tab({ shift: true })
      expect(dialogo).toContainElement(document.activeElement)
    }
  })

  it('desde el último elemento, Tab vuelve al primero', async () => {
    mostrar(<Modal abierto onCerrar={() => {}} titulo="X" pie={<button>Guardar</button>} />)
    screen.getByRole('button', { name: 'Guardar' }).focus()
    await userEvent.tab()
    expect(screen.getByRole('button', { name: 'Cerrar' })).toHaveFocus()
  })

  it('al cerrarla, el foco vuelve al botón que la abrió', async () => {
    mostrar(<Ejemplo />)
    const abrir = screen.getByRole('button', { name: 'Abrir' })
    await userEvent.click(abrir)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(abrir).toHaveFocus()
  })

  it('mientras está abierta el fondo no scrollea y queda inerte; al cerrar se libera', async () => {
    mostrar(<Ejemplo />)
    await userEvent.click(screen.getByRole('button', { name: 'Abrir' }))
    expect(document.body.style.overflow).toBe('hidden')
    expect(raiz).toHaveAttribute('inert')
    await userEvent.keyboard('{Escape}')
    expect(document.body.style.overflow).toBe('')
    expect(raiz).not.toHaveAttribute('inert')
  })

  it('al desmontarla con la ventana abierta también se libera el fondo', () => {
    const { unmount } = mostrar(<Modal abierto onCerrar={() => {}} titulo="X" />)
    expect(raiz).toHaveAttribute('inert')
    unmount()
    expect(raiz).not.toHaveAttribute('inert')
    expect(document.body.style.overflow).toBe('')
  })

  describe('tocar el fondo', () => {
    it('la cierra por defecto', async () => {
      const onCerrar = vi.fn()
      mostrar(<Modal abierto onCerrar={onCerrar} titulo="X" />)
      await userEvent.click(document.querySelector('.ui-modal-fondo'))
      expect(onCerrar).toHaveBeenCalledTimes(1)
    })

    it('no la cierra si hay cambios sin guardar (cerrarAlTocarFuera=false)', async () => {
      const onCerrar = vi.fn()
      mostrar(<Modal abierto onCerrar={onCerrar} titulo="X" cerrarAlTocarFuera={false} />)
      await userEvent.click(document.querySelector('.ui-modal-fondo'))
      expect(onCerrar).not.toHaveBeenCalled()
    })

    it('tocar adentro de la ventana no la cierra', async () => {
      const onCerrar = vi.fn()
      mostrar(<Modal abierto onCerrar={onCerrar} titulo="X">Contenido</Modal>)
      await userEvent.click(screen.getByText('Contenido'))
      expect(onCerrar).not.toHaveBeenCalled()
    })
  })

  it('con dos ventanas apiladas, Escape cierra solo la de arriba', async () => {
    const cerrarDeAbajo = vi.fn()
    const cerrarDeArriba = vi.fn()
    mostrar(
      <>
        <Modal abierto onCerrar={cerrarDeAbajo} titulo="De abajo" />
        <Modal abierto onCerrar={cerrarDeArriba} titulo="De arriba" />
      </>
    )
    await userEvent.keyboard('{Escape}')
    expect(cerrarDeArriba).toHaveBeenCalledTimes(1)
    expect(cerrarDeAbajo).not.toHaveBeenCalled()
  })

  describe('hoja de celular: deslizar hacia abajo desde la manija', () => {
    const arrastrar = (manija, desde, hasta) => {
      const evento = (tipo, y) =>
        new MouseEvent(tipo, { bubbles: true, clientY: y }) // jsdom no trae PointerEvent
      act(() => {
        manija.dispatchEvent(evento('pointerdown', desde))
        manija.dispatchEvent(evento('pointermove', hasta))
        manija.dispatchEvent(evento('pointerup', hasta))
      })
    }

    it('un arrastre largo la cierra', () => {
      const onCerrar = vi.fn()
      mostrar(<Modal abierto onCerrar={onCerrar} titulo="X" />)
      arrastrar(document.querySelector('.ui-modal-manija'), 100, 260)
      expect(onCerrar).toHaveBeenCalledTimes(1)
    })

    it('un arrastre corto no la cierra y vuelve a su lugar', () => {
      const onCerrar = vi.fn()
      mostrar(<Modal abierto onCerrar={onCerrar} titulo="X" />)
      arrastrar(document.querySelector('.ui-modal-manija'), 100, 130)
      expect(onCerrar).not.toHaveBeenCalled()
      expect(screen.getByRole('dialog').style.transform).toBe('')
    })

    it('arrastrar hacia arriba no hace nada', () => {
      const onCerrar = vi.fn()
      mostrar(<Modal abierto onCerrar={onCerrar} titulo="X" />)
      arrastrar(document.querySelector('.ui-modal-manija'), 300, 50)
      expect(onCerrar).not.toHaveBeenCalled()
    })

    it('la manija es decorativa: no está en el árbol de accesibilidad', () => {
      mostrar(<Modal abierto onCerrar={() => {}} titulo="X" />)
      expect(document.querySelector('.ui-modal-manija')).toHaveAttribute('aria-hidden', 'true')
    })
  })
})
