import { describe, expect, it } from 'vitest'
import { recortar } from './useMaquinaDeEscribir'

describe('recortar', () => {
  it('sin formato corta tal cual', () => {
    expect(recortar('Hola mundo', 4)).toBe('Hola')
    expect(recortar('Hola', 99)).toBe('Hola')
  })

  it('cierra una negrita que quedó abierta, para que no se vean asteriscos sueltos', () => {
    expect(recortar('Tenés **dos** trabajos', 10)).toBe('Tenés **do**')
    expect(recortar('Tenés **dos** trabajos', 12)).toBe('Tenés **dos**')
  })

  it('oculta el asterisco que es la mitad de una apertura', () => {
    expect(recortar('Tenés **dos** trabajos', 7)).toBe('Tenés ')
  })

  it('una lista cortada a la mitad sigue siendo texto válido', () => {
    expect(recortar('- uno\n- dos', 9)).toBe('- uno\n- d')
  })
})
