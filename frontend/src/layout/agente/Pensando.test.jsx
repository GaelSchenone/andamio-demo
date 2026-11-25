import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Pensando, { FRASES, otraFrase } from './Pensando'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

const frase = () => document.querySelector('.agente-pensando-frase').textContent

describe('Pensando', () => {
  it('muestra una frase de la lista y la cambia cada pocos segundos', () => {
    render(<Pensando />)
    const primera = frase()
    expect(FRASES).toContain(primera)
    act(() => vi.advanceTimersByTime(2600))
    expect(FRASES).toContain(frase())
    expect(frase()).not.toBe(primera)
  })

  it('muestra los segundos recién a partir de los 5', () => {
    render(<Pensando />)
    act(() => vi.advanceTimersByTime(3000))
    expect(document.querySelector('.agente-pensando-tiempo')).toBeNull()
    act(() => vi.advanceTimersByTime(3000))
    expect(document.querySelector('.agente-pensando-tiempo').textContent).toBe('6 s')
  })

  it('los lectores de pantalla oyen un solo "Pensando…" y no cada frase', () => {
    render(<Pensando />)
    expect(screen.getByRole('status')).toHaveTextContent('Pensando…')
    expect(document.querySelector('.agente-pensando-frase')).toHaveAttribute('aria-hidden', 'true')
  })

  it('otraFrase nunca repite la anterior', () => {
    for (let anterior = 0; anterior < FRASES.length; anterior += 1) {
      for (let intento = 0; intento < 50; intento += 1) {
        const nueva = otraFrase(anterior)
        expect(nueva).not.toBe(anterior)
        expect(nueva).toBeGreaterThanOrEqual(0)
        expect(nueva).toBeLessThan(FRASES.length)
      }
    }
  })
})
