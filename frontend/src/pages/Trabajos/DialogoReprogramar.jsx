import { useState } from 'react'
import { api } from '../../api'
import { CAUSAS } from '../../constantes'
import { formatoFecha } from '../../formato'
import { Alerta, Button, Input, Modal, Select } from '../../ui'
import './Trabajos.css'

/** Último paso de reprogramar: los días ya se eligieron en el calendario; acá se dice por qué se cambian. */
export default function DialogoReprogramar({ trabajo: t, dias, onCerrar, onHecho }) {
  const [causa, setCausa] = useState('clima')
  const [motivo, setMotivo] = useState('')
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)

  async function guardar(e) {
    e.preventDefault()
    setError('')
    setOcupado(true)
    try {
      await api.reprogramarTrabajo(t.id, { dias, causa, motivo: motivo.trim() })
      onHecho('Trabajo reprogramado. El cambio quedó registrado.')
    } catch (err) {
      setError(err.message)
      setOcupado(false)
    }
  }

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      titulo="Reprogramar trabajo"
      descripcion={`${t.cliente.nombre} · ${dias.length} ${dias.length === 1 ? 'día' : 'días'}, del ${formatoFecha(dias[0])} al ${formatoFecha(dias.at(-1))}`}
      pie={
        <>
          <Button onClick={onCerrar} disabled={ocupado}>
            Volver al calendario
          </Button>
          <Button type="submit" form="form-reprogramar" variante="primario" cargando={ocupado}>
            Guardar cambio
          </Button>
        </>
      }
    >
      <form id="form-reprogramar" className="trabajos-form" onSubmit={guardar}>
        <Select etiqueta="¿Por qué se cambia?" value={causa} onChange={(e) => setCausa(e.target.value)} data-autofocus>
          {Object.entries(CAUSAS).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </Select>
        <Input etiqueta="Detalle" opcional value={motivo} maxLength={500} onChange={(e) => setMotivo(e.target.value)} placeholder="Ej: llovió toda la semana" />
        {error && <Alerta>{error}</Alerta>}
      </form>
    </Modal>
  )
}
