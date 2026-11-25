import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api'
import { instalarMatchMedia } from '../../test/simularAncho'
import { SesionContexto } from '../sesion'
import AgenteChat from './AgenteChat'

vi.mock('../../api', () => ({ api: { estadoAgente: vi.fn(), chatAgente: vi.fn() } }))

const Ruta = () => <p data-testid="ruta">{useLocation().pathname}</p>

function montar(rol = 'dueno') {
  const yo = { id: 1, nombre: 'Dora López', usuario: 'dora', rol }
  return render(
    <SesionContexto.Provider value={{ yo, esDueno: rol === 'dueno' }}>
      <MemoryRouter>
        <Routes>
          <Route path="*" element={<><AgenteChat /><Ruta /></>} />
        </Routes>
      </MemoryRouter>
    </SesionContexto.Provider>
  )
}

beforeEach(() => {
  instalarMatchMedia(1280, { reducirMovimiento: true }) // sin máquina de escribir: la respuesta aparece entera
  api.estadoAgente.mockResolvedValue({ disponible: true })
  api.chatAgente.mockResolvedValue({ respuesta: 'Tenés **dos** trabajos:\n- Los Álamos\n- Familia Gómez', acciones: [{ ruta: '/trabajos?vista=semana', etiqueta: 'Ir a Trabajos (semana)' }] })
})

afterEach(() => {
  vi.clearAllMocks()
  delete window.webkitSpeechRecognition
})

const abrir = async () => userEvent.click(await screen.findByRole('button', { name: 'Abrir el asistente' }))

describe('Asistente', () => {
  it('no aparece si el servidor no tiene Gemini', async () => {
    api.estadoAgente.mockResolvedValue({ disponible: false })
    montar()
    await waitFor(() => expect(api.estadoAgente).toHaveBeenCalled())
    expect(screen.queryByRole('button', { name: /asistente/i })).toBeNull()
  })

  it('avisa que las respuestas son simuladas en la versión de demostración', async () => {
    api.estadoAgente.mockResolvedValue({ disponible: true, simulado: true })
    montar()
    await abrir()
    expect(screen.getByText('Modo demo: respuestas simuladas')).toBeInTheDocument()
  })

  it('no muestra el aviso de demo con el asistente real', async () => {
    montar()
    await abrir()
    expect(screen.queryByText(/Modo demo/)).toBeNull()
  })

  it('se abre con sugerencias según el rol y saluda por el nombre', async () => {
    montar('empleado')
    await abrir()
    expect(screen.getByRole('dialog', { name: 'Asistente de Andamio' })).toBeInTheDocument()
    expect(screen.getByText(/Hola, Dora/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '¿Cómo inicio un trabajo?' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Cuánto me deben/ })).toBeNull()
  })

  it('manda la pregunta, muestra la respuesta con negritas y listas, y el botón lleva a la pantalla', async () => {
    montar()
    await abrir()
    await userEvent.type(screen.getByLabelText('Escribile al asistente'), '¿qué tengo esta semana?{Enter}')
    expect(api.chatAgente).toHaveBeenCalledWith([{ rol: 'usuario', texto: '¿qué tengo esta semana?' }], null)
    const log = screen.getByRole('log')
    expect(await within(log).findByText('dos')).toHaveProperty('tagName', 'STRONG')
    expect(within(log).getAllByRole('listitem').map((li) => li.textContent)).toEqual(['Los Álamos', 'Familia Gómez'])
    await userEvent.click(screen.getByRole('button', { name: 'Ir a Trabajos (semana)' }))
    expect(screen.getByTestId('ruta')).toHaveTextContent('/trabajos')
  })

  it('una sugerencia se envía sola, y la conversación se manda completa en la siguiente', async () => {
    montar()
    await abrir()
    await userEvent.click(screen.getByRole('button', { name: '¿Cuánto me deben en total?' }))
    await screen.findByText('Los Álamos')
    await userEvent.type(screen.getByLabelText('Escribile al asistente'), 'y mañana?{Enter}')
    await waitFor(() => expect(api.chatAgente).toHaveBeenCalledTimes(2))
    expect(api.chatAgente.mock.calls[1][0].map((m) => m.rol)).toEqual(['usuario', 'agente', 'usuario'])
  })

  it('reenvía el id de la conversación que devolvió el servidor, y lo suelta al empezar una nueva', async () => {
    api.chatAgente.mockResolvedValue({ respuesta: 'Hola', acciones: [], conversacion_id: 'conv-7' })
    montar()
    await abrir()
    await userEvent.type(screen.getByLabelText('Escribile al asistente'), 'uno{Enter}')
    await screen.findByText('Hola')
    await userEvent.type(screen.getByLabelText('Escribile al asistente'), 'dos{Enter}')
    await waitFor(() => expect(api.chatAgente).toHaveBeenCalledTimes(2))
    expect(api.chatAgente.mock.calls[1][1]).toBe('conv-7')
    await userEvent.click(screen.getByRole('button', { name: 'Empezar una conversación nueva' }))
    await userEvent.type(screen.getByLabelText('Escribile al asistente'), 'tres{Enter}')
    await waitFor(() => expect(api.chatAgente).toHaveBeenCalledTimes(3))
    expect(api.chatAgente.mock.calls[2][1]).toBeNull()
  })

  it('con movimiento normal la respuesta se escribe de a poco y los botones aparecen al terminar; tocarla la muestra entera', async () => {
    instalarMatchMedia(1280, { reducirMovimiento: false })
    const larga = 'Esta semana tenés varios trabajos para revisar con calma. '.repeat(8)
    api.chatAgente.mockResolvedValue({ respuesta: larga, acciones: [{ ruta: '/trabajos', etiqueta: 'Ir a Trabajos' }] })
    montar()
    await abrir()
    await userEvent.type(screen.getByLabelText('Escribile al asistente'), 'hola{Enter}')
    const tipeando = await waitFor(() => {
      const el = document.querySelector('.agente-tipeando')
      expect(el).not.toBeNull()
      return el
    })
    const visible = () => tipeando.querySelector('[aria-hidden]').textContent
    expect(visible().length).toBeLessThan(larga.trim().length)
    expect(screen.queryByRole('button', { name: 'Ir a Trabajos' })).toBeNull()
    expect(within(tipeando).getByText(larga.trim(), { selector: '.sr-only' })).toBeInTheDocument() // los lectores de pantalla reciben todo junto
    await userEvent.click(tipeando)
    expect(document.querySelector('.agente-tipeando')).toBeNull()
    expect(screen.getByRole('button', { name: 'Ir a Trabajos' })).toBeInTheDocument()
  })

  it('si falla, muestra el mensaje del servidor', async () => {
    api.chatAgente.mockRejectedValue(new Error('El asistente no está disponible en este momento.'))
    montar()
    await abrir()
    await userEvent.type(screen.getByLabelText('Escribile al asistente'), 'hola{Enter}')
    expect(await screen.findByRole('alert')).toHaveTextContent('no está disponible')
  })

  it('el texto de la respuesta nunca se interpreta como HTML', async () => {
    api.chatAgente.mockResolvedValue({ respuesta: '<img src=x onerror=alert(1)> **ok**', acciones: [] })
    montar()
    await abrir()
    await userEvent.type(screen.getByLabelText('Escribile al asistente'), 'hola{Enter}')
    await screen.findByText('ok')
    expect(document.querySelector('.agente-mensaje img')).toBeNull()
  })

  it('Escape cierra el chat y devuelve el foco a la orbe', async () => {
    montar()
    await abrir()
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(screen.getByRole('button', { name: 'Abrir el asistente' })).toHaveFocus()
  })

  it('el micrófono solo aparece si el navegador sabe dictar', async () => {
    montar()
    await abrir()
    expect(screen.queryByRole('button', { name: 'Dictar con la voz' })).toBeNull()
  })

  it('con dictado disponible, lo que se dicta va al campo de texto', async () => {
    let reconocedor
    window.webkitSpeechRecognition = function () {
      reconocedor = this
      this.start = vi.fn()
      this.stop = vi.fn()
      this.abort = vi.fn()
    }
    montar()
    await abrir()
    await userEvent.click(screen.getByRole('button', { name: 'Dictar con la voz' }))
    expect(reconocedor.start).toHaveBeenCalled()
    expect(reconocedor.lang).toBe('es-AR')
    reconocedor.onresult({ results: [Object.assign([{ transcript: 'cómo agendo un trabajo' }], { isFinal: true })] })
    await waitFor(() => expect(screen.getByLabelText('Escribile al asistente')).toHaveValue('cómo agendo un trabajo'))
    reconocedor.onerror({ error: 'not-allowed' })
    expect(await screen.findByText(/permiso para usar el micrófono/)).toBeInTheDocument()
  })
})
