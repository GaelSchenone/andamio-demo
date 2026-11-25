import { CircleCheck, Plus } from 'lucide-react'
import { Input } from '../../ui'
import './CampoBuscador.css'

/**
 * Campo de texto que busca mientras se escribe: debajo muestra las coincidencias que ya existen (para
 * elegirlas con un toque) y, si lo escrito no existe, la opción de crearlo. Así se evita cargar dos veces
 * el mismo cliente o la misma dirección.
 * `elegido`: ya se eligió algo de la lista (se muestra un tilde y se ocultan las sugerencias).
 */
export default function CampoBuscador({ etiqueta, valor, onTexto, elegido, opciones, textoCrear, onCrear, avisoDeCoincidencias, ayuda, deshabilitado, ...resto }) {
  const hayAlgoParaMostrar = !elegido && !deshabilitado && (opciones.length > 0 || textoCrear)
  return (
    <div className="buscador-campo">
      <Input etiqueta={etiqueta} value={valor} onChange={(e) => onTexto(e.target.value)} disabled={deshabilitado} autoComplete="off" ayuda={ayuda} {...resto} />
      {elegido && (
        <p className="buscador-elegido">
          <CircleCheck size={16} aria-hidden="true" /> Elegido de la lista
        </p>
      )}
      {hayAlgoParaMostrar && (
        <div className="buscador-sugerencias">
          {opciones.length > 0 && avisoDeCoincidencias && <p className="buscador-aviso">{avisoDeCoincidencias}</p>}
          <ul aria-label={`Coincidencias de ${etiqueta}`}>
            {opciones.map((o) => (
              <li key={o.id}>
                <button type="button" onClick={() => o.elegir()}>
                  <strong>{o.titulo}</strong>
                  {o.detalle && <small>{o.detalle}</small>}
                </button>
              </li>
            ))}
            {textoCrear && (
              <li>
                <button type="button" className="buscador-crear" onClick={onCrear}>
                  <Plus size={18} aria-hidden="true" /> {textoCrear}
                </button>
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  )
}
