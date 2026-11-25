import { useCallback, useState } from 'react'
import { api } from '../../api'
import { CONCEPTOS_COBRO, pesos } from '../../constantes'
import useCargar from '../../hooks/useCargar'
import { formatoFecha, hoyISO } from '../../formato'
import { Alerta, Badge, Button, Input, Kpi, Select, Skeleton, useAvisar, useConfirmar } from '../../ui'
import './Cobros.css'

/**
 * Los cobros de un trabajo: cuánto falta, qué se cobró y un formulario para registrar otro pago.
 * Un cobro no se edita ni se borra: si se cargó mal, se anula (queda registrado y deja de contar).
 */
export default function CobrosDelTrabajo({ trabajoId, alCambiar }) {
  const avisar = useAvisar()
  const confirmar = useConfirmar()
  const { datos: resumen, error, setDatos } = useCargar(useCallback(() => api.cobrosDeTrabajo(trabajoId), [trabajoId]), [trabajoId])
  const [concepto, setConcepto] = useState('sena')
  const [monto, setMonto] = useState('') // vacío = se usa el monto sugerido
  const [fecha, setFecha] = useState(hoyISO())
  const [nota, setNota] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [errorForm, setErrorForm] = useState('')

  if (error && !resumen) return <Alerta>{error}</Alerta>
  if (!resumen) return <Skeleton alto="8rem" />

  const sugerido = concepto === 'sena' ? resumen.sugerido_sena : resumen.sugerido_saldo
  const montoAMostrar = monto !== '' ? monto : sugerido > 0 ? String(sugerido) : ''

  async function registrar(e) {
    e.preventDefault()
    setErrorForm('')
    const importe = Number(montoAMostrar)
    if (!(importe > 0)) return setErrorForm('Ingresá un monto mayor a cero.')
    setOcupado(true)
    try {
      setDatos(await api.registrarCobro(trabajoId, { concepto, monto: importe, fecha, nota }))
      setMonto('')
      setNota('')
      avisar('Cobro registrado.')
      alCambiar?.()
    } catch (err) {
      setErrorForm(err.message)
    } finally {
      setOcupado(false)
    }
  }

  async function anular(cobro) {
    const si = await confirmar({
      titulo: '¿Anular este cobro?',
      mensaje: `${pesos(cobro.monto)} del ${formatoFecha(cobro.fecha)}. Deja de contar, pero queda registrado.`,
      confirmarLabel: 'Anular cobro',
      peligro: true,
    })
    if (!si) return
    setOcupado(true)
    try {
      setDatos(await api.anularCobro(cobro.id))
      avisar('Cobro anulado.')
      alCambiar?.()
    } catch (err) {
      setErrorForm(err.message)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <div className="cobros-trabajo">
      <div className="cobros-kpis">
        <Kpi etiqueta="Total" valor={pesos(resumen.total)} />
        <Kpi etiqueta="Cobrado" valor={pesos(resumen.cobrado)} />
        <Kpi etiqueta="Falta" valor={pesos(resumen.pendiente)} />
      </div>

      {resumen.cobros.length > 0 && (
        <ul className="cobros-lista" aria-label="Cobros registrados">
          {resumen.cobros.map((c) => (
            <li key={c.id} className={c.anulado ? 'is-anulado' : undefined}>
              <div>
                <strong>
                  {CONCEPTOS_COBRO[c.concepto]} {pesos(c.monto)}
                </strong>{' '}
                · {formatoFecha(c.fecha)}
                {c.nota ? ` · ${c.nota}` : ''}
                <small>
                  {c.usuario_nombre}
                  {c.anulado && ` · anulado el ${formatoFecha(c.anulado_en.slice(0, 10))}`}
                </small>
              </div>
              {c.anulado ? (
                <Badge tono="neutro">Anulado</Badge>
              ) : (
                <Button tamano="sm" variante="peligro" disabled={ocupado} onClick={() => anular(c)}>
                  Anular
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {resumen.pendiente > 0 ? (
        <form className="cobros-form" onSubmit={registrar}>
          <h3>Registrar un cobro</h3>
          <div className="cobros-fila">
            <Select
              etiqueta="Concepto"
              value={concepto}
              onChange={(e) => {
                setConcepto(e.target.value)
                setMonto('') // vuelve a proponer el monto que corresponde a ese concepto
              }}
            >
              <option value="sena">Seña (50%)</option>
              <option value="saldo">Saldo</option>
            </Select>
            <Input etiqueta="Monto ($)" type="number" inputMode="decimal" min="0.01" step="0.01" value={montoAMostrar} onChange={(e) => setMonto(e.target.value)} />
          </div>
          <div className="cobros-fila">
            <Input etiqueta="Fecha del pago" type="date" max={hoyISO()} value={fecha} onChange={(e) => setFecha(e.target.value)} />
            <Input etiqueta="Nota" opcional value={nota} maxLength={500} onChange={(e) => setNota(e.target.value)} placeholder="Ej: efectivo, transferencia" />
          </div>
          {errorForm && <Alerta>{errorForm}</Alerta>}
          <div>
            <Button type="submit" variante="primario" cargando={ocupado}>
              Registrar cobro
            </Button>
          </div>
        </form>
      ) : (
        <Alerta tono="ok">No falta cobrar nada de este trabajo.</Alerta>
      )}
      {!resumen.pendiente && errorForm && <Alerta>{errorForm}</Alerta>}
    </div>
  )
}
