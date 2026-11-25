import { useState } from 'react'
import { api } from '../../api'
import { Alerta, Button, Input, Modal, Select, Textarea } from '../../ui'
import './Clientes.css'

// Mismos largos máximos que valida el backend (schemas_clientes.py).
const MAX = { nombre: 150, telefono: 40, notas: 1000 }

/** Ventana de cliente, compartida entre "nuevo" y "editar". Si falla, muestra el mensaje del servidor. */
export default function ClienteFormulario({ abierto, cliente, nombreInicial, onCerrar, onGuardado }) {
  const [datos, setDatos] = useState(() => desde(cliente, nombreInicial))
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)
  const campo = (n) => (e) => setDatos((d) => ({ ...d, [n]: e.target.value }))

  async function enviar(e) {
    e.preventDefault()
    setError('')
    setGuardando(true)
    try {
      const guardado = cliente ? await api.actualizarCliente(cliente.id, datos) : await api.crearCliente(datos)
      if (!cliente) setDatos(desde(null, ''))
      onGuardado(guardado)
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
      titulo={cliente ? 'Editar cliente' : 'Nuevo cliente'}
      pie={
        <>
          <Button onClick={onCerrar}>Cancelar</Button>
          <Button type="submit" form="form-cliente" variante="primario" cargando={guardando} disabled={!datos.nombre.trim()}>
            {cliente ? 'Guardar cambios' : 'Crear cliente'}
          </Button>
        </>
      }
    >
      <form id="form-cliente" className="form-columnas" onSubmit={enviar}>
        <Input etiqueta="Nombre" value={datos.nombre} onChange={campo('nombre')} maxLength={MAX.nombre} placeholder="Nombre y apellido, o nombre del consorcio" data-autofocus />
        <Select etiqueta="Tipo" value={datos.tipo} onChange={campo('tipo')}>
          <option value="casa">Casa</option>
          <option value="consorcio">Consorcio</option>
        </Select>
        <Input etiqueta="Teléfono" type="tel" inputMode="tel" value={datos.telefono} onChange={campo('telefono')} maxLength={MAX.telefono} opcional />
        <Textarea etiqueta="Notas" value={datos.notas} onChange={campo('notas')} maxLength={MAX.notas} placeholder="Ej: prefiere que lo llamen de tarde" opcional />
        {error && <Alerta>{error}</Alerta>}
      </form>
    </Modal>
  )
}

const desde = (c, nombre = '') => ({ nombre: c?.nombre ?? nombre, tipo: c?.tipo ?? 'casa', telefono: c?.telefono ?? '', notas: c?.notas ?? '' })
