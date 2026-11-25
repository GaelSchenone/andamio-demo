import { Trash2 } from 'lucide-react'
import { LARGO_MAXIMO } from '../../limites'
import { IconButton, Input } from '../../ui'
import './Editor.css'

/** Un trabajo del presupuesto: descripción, unidad, cantidad e importe. `brillos` marca lo que acaba de escribir la IA. */
export default function ItemEditor({ item, index, onChange, onQuitar, puedeQuitar, brillos }) {
  const brillo = (campo) => (brillos.has(`items.${index}.${campo}`) ? 'brillo' : undefined)
  return (
    <fieldset className="item-editor">
      <legend>Trabajo {index + 1}</legend>
      {puedeQuitar && <IconButton icono={Trash2} etiqueta={`Quitar trabajo ${index + 1}`} className="item-editor-quitar" onClick={onQuitar} />}
      <Input
        id={`descripcion-${index}`}
        etiqueta="Descripción del trabajo"
        className={brillo('descripcion')}
        placeholder="Ej: Pintura de living y comedor (látex interior)"
        maxLength={LARGO_MAXIMO.descripcion}
        value={item.descripcion}
        onChange={(e) => onChange('descripcion', e.target.value)}
      />
      <div className="item-editor-fila">
        <Input id={`unidad-${index}`} etiqueta="Unidad" className={brillo('unidad')} placeholder="m2, gl, día…" maxLength={LARGO_MAXIMO.unidad} value={item.unidad} onChange={(e) => onChange('unidad', e.target.value)} />
        <Input id={`cantidad-${index}`} etiqueta="Cantidad" className={brillo('cantidad')} type="number" inputMode="decimal" min="0" step="any" placeholder="0" value={item.cantidad} onChange={(e) => onChange('cantidad', e.target.value)} />
        <Input id={`importe-${index}`} etiqueta="Importe ($)" className={brillo('importe')} type="number" inputMode="decimal" min="0" step="any" placeholder="0" value={item.importe} onChange={(e) => onChange('importe', e.target.value)} />
      </div>
    </fieldset>
  )
}
