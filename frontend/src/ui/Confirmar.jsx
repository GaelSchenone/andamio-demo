import { createContext, useCallback, useContext, useState } from 'react'
import Button from './Button'
import Modal from './Modal'

const Contexto = createContext(null)

/**
 * Reemplaza a window.confirm. Se usa así:
 *   const confirmar = useConfirmar()
 *   if (await confirmar({ titulo: '¿Eliminar el cliente?', mensaje: '…', confirmarLabel: 'Eliminar', peligro: true })) …
 *
 * El foco arranca en "Cancelar": una confirmación de algo destructivo no se acepta con un Enter distraído.
 * Escape, ✕ y tocar afuera equivalen a cancelar.
 */
export function ConfirmarProvider({ children }) {
  const [pendiente, setPendiente] = useState(null)

  const confirmar = useCallback(
    (opciones) => new Promise((resolver) => setPendiente({ opciones, resolver })),
    []
  )

  function responder(valor) {
    pendiente.resolver(valor)
    setPendiente(null)
  }

  const { titulo, mensaje, confirmarLabel = 'Confirmar', cancelarLabel = 'Cancelar', peligro = false } =
    pendiente?.opciones ?? {}

  return (
    <Contexto.Provider value={confirmar}>
      {children}
      <Modal
        abierto={Boolean(pendiente)}
        onCerrar={() => responder(false)}
        titulo={titulo}
        descripcion={mensaje}
        tamano="sm"
        pie={
          <>
            <Button data-autofocus onClick={() => responder(false)}>
              {cancelarLabel}
            </Button>
            <Button variante={peligro ? 'peligro-solido' : 'primario'} onClick={() => responder(true)}>
              {confirmarLabel}
            </Button>
          </>
        }
      />
    </Contexto.Provider>
  )
}

export function useConfirmar() {
  const confirmar = useContext(Contexto)
  if (!confirmar) throw new Error('useConfirmar necesita estar dentro de <ConfirmarProvider>.')
  return confirmar
}
