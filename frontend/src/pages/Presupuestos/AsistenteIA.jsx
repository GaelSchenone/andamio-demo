import { Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Alerta, Button, Panel, Textarea } from '../../ui'
import './Editor.css'

const FRASES = [
  'Leyendo el pedido del cliente…',
  'Separando los trabajos…',
  'Sacando medidas y cantidades…',
  'Acomodando las condiciones…',
  'Dándole los últimos toques…',
]

// estado: null (quieto) | "pensando" (esperando a Gemini) | "escribiendo" (animando)
export default function AsistenteIA({ panelRef, estado, error, aviso, onCompletar }) {
  const [mensaje, setMensaje] = useState('')
  const [frase, setFrase] = useState(0)
  const trabajando = estado !== null

  useEffect(() => {
    if (estado !== 'pensando') return undefined
    const id = setInterval(() => setFrase((f) => Math.min(f + 1, FRASES.length - 1)), 1800)
    return () => clearInterval(id)
  }, [estado])

  function completar() {
    if (trabajando || mensaje.trim().length < 3) return
    setFrase(0)
    onCompletar(mensaje.trim())
  }

  const etiqueta = estado === 'pensando' ? FRASES[frase] : estado === 'escribiendo' ? 'Completando el presupuesto…' : 'Completar presupuesto'

  return (
    <div ref={panelRef}>
      <Panel titulo="Completar con IA" icono={Sparkles}>
        <div className="editor-ia">
          <p className="editor-ayuda">
            Escribí los trabajos como te salga: la IA los pasa en limpio y completa plazos y condiciones. El cliente y la obra los elegís vos abajo. Después revisalo y completá los importes.
          </p>
          <Textarea
            etiqueta="Qué hay que presupuestar"
            placeholder="Ej: pintar living unos 40m2 q esta descascarado y cambiar 3 enchufes cocina, 45 lucas los enchufes. materiales ponemos nosotros"
            value={mensaje}
            rows={4}
            onChange={(e) => setMensaje(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault()
                completar()
              }
            }}
            disabled={trabajando}
          />
          {error && <Alerta>{error}</Alerta>}
          {aviso && !trabajando && <Alerta tono="ok">{aviso}</Alerta>}
          <div>
            <Button variante="primario" icono={Sparkles} cargando={trabajando} disabled={mensaje.trim().length < 3} onClick={completar}>
              {etiqueta}
            </Button>
          </div>
        </div>
      </Panel>
    </div>
  )
}
