import { useState } from 'react'
import { api } from '../../api'
import { Alerta, Button, Input, Modal, Textarea } from '../../ui'
import './Clientes.css'

// Mismos largos máximos que valida el backend (schemas_clientes.py).
const MAX = { direccion: 300, referencia: 100, notas: 1000 }

/** Ventana de obra (una dirección de un cliente): `obra` si se edita, `clienteId` si se agrega. */
export default function ObraFormulario({ abierto, clienteId, obra, direccionInicial, onCerrar, onGuardado }) {
  const [datos, setDatos] = useState(() => desde(obra, direccionInicial))
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)
  const campo = (n) => (e) => setDatos((d) => ({ ...d, [n]: e.target.value }))

  async function enviar(e) {
    e.preventDefault()
    setError('')
    setGuardando(true)
    try {
      const guardada = obra ? await api.actualizarObra(obra.id, datos) : await api.crearObra(clienteId, datos)
      if (!obra) setDatos(desde(null, ''))
      onGuardado(guardada)
    } catch (err) {
      setError(err.message)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <Modal
      abierto={abierto}
      onCerrar={onCerrar}
      titulo={obra ? 'Editar obra' : 'Nueva obra'}
      pie={
        <>
          <Button onClick={onCerrar}>Cancelar</Button>
          <Button type="submit" form="form-obra" variante="primario" cargando={guardando} disabled={!datos.direccion.trim()}>
            {obra ? 'Guardar obra' : 'Agregar obra'}
          </Button>
        </>
      }
    >
      <form id="form-obra" className="form-columnas" onSubmit={enviar}>
        <Input etiqueta="Dirección" value={datos.direccion} onChange={campo('direccion')} maxLength={MAX.direccion} placeholder="Calle, número, localidad" data-autofocus />
        <Input etiqueta="Referencia" value={datos.referencia} onChange={campo('referencia')} maxLength={MAX.referencia} placeholder="Ej: Depto 3B, Hall y escaleras, Fondo" opcional />
        <Textarea etiqueta="Notas para la obra" value={datos.notas} onChange={campo('notas')} maxLength={MAX.notas} placeholder="Ej: timbre roto, la llave la tiene el encargado" rows={2} opcional />
        {error && <Alerta>{error}</Alerta>}
      </form>
    </Modal>
  )
}

const desde = (o, direccion = '') => ({ direccion: o?.direccion ?? direccion, referencia: o?.referencia ?? '', notas: o?.notas ?? '' })
