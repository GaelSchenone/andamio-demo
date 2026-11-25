import { MapPin, Pencil, Phone, Plus, Trash2 } from 'lucide-react'
import { useCallback, useState } from 'react'
import { api } from '../../api'
import { TIPOS_CLIENTE } from '../../constantes'
import { urlMapa, urlTelefono } from '../../enlaces'
import useCargar from '../../hooks/useCargar'
import { useSesion } from '../../layout/sesion'
import { Alerta, Badge, Button, Skeleton, useAvisar, useConfirmar } from '../../ui'
import ClienteFormulario from './ClienteFormulario'
import ObraFormulario from './ObraFormulario'
import './Clientes.css'

export default function ClienteDetalle({ id, alCambiar, alEliminar }) {
  const { esDueno } = useSesion()
  const avisar = useAvisar()
  const confirmar = useConfirmar()
  const { datos: cliente, error, recargar } = useCargar(useCallback(() => api.obtenerCliente(id), [id]), [id])
  const [editando, setEditando] = useState(false)
  const [obraEnEdicion, setObraEnEdicion] = useState(null) // null | 'nueva' | obra

  async function eliminarCliente() {
    const si = await confirmar({
      titulo: `¿Eliminar a ${cliente.nombre}?`,
      mensaje: 'Se borran sus datos y no se puede deshacer.',
      confirmarLabel: 'Eliminar cliente',
      peligro: true,
    })
    if (!si) return
    try {
      await api.eliminarCliente(id)
      avisar('Cliente eliminado.')
      alEliminar()
    } catch (err) {
      avisar(err.message, { tono: 'peligro' }) // por ejemplo: "tiene obras cargadas"
    }
  }

  async function eliminarObra(obra) {
    const si = await confirmar({
      titulo: '¿Eliminar la obra?',
      mensaje: obra.direccion,
      confirmarLabel: 'Eliminar obra',
      peligro: true,
    })
    if (!si) return
    try {
      await api.eliminarObra(obra.id)
      avisar('Obra eliminada.')
      recargar()
      alCambiar()
    } catch (err) {
      avisar(err.message, { tono: 'peligro' })
    }
  }

  if (error) return <Alerta>{error}</Alerta>
  if (!cliente) {
    return (
      <div aria-busy="true" className="cliente-detalle">
        <Skeleton alto="2rem" ancho="60%" />
        <Skeleton alto="4rem" />
      </div>
    )
  }

  return (
    <div className="cliente-detalle">
      <div className="cliente-encabezado">
        <h2>{cliente.nombre}</h2>
        <div>
          <Badge>{TIPOS_CLIENTE[cliente.tipo]}</Badge>
        </div>
        {cliente.telefono && (
          <div className="cliente-enlaces">
            <a className="ui-btn ui-btn--secundario ui-btn--sm" href={urlTelefono(cliente.telefono)}>
              <Phone size={18} aria-hidden="true" /> {cliente.telefono}
            </a>
          </div>
        )}
        {cliente.notas && <p className="cliente-notas">{cliente.notas}</p>}
        {esDueno && (
          <div className="cliente-acciones">
            <Button tamano="sm" icono={Pencil} onClick={() => setEditando(true)}>
              Editar
            </Button>
            <Button tamano="sm" variante="peligro" icono={Trash2} onClick={eliminarCliente}>
              Eliminar
            </Button>
          </div>
        )}
      </div>

      <section aria-labelledby="titulo-obras">
        <div className="obras-titulo">
          <h3 id="titulo-obras">Obras</h3>
          {esDueno && (
            <Button tamano="sm" icono={Plus} onClick={() => setObraEnEdicion('nueva')}>
              Agregar obra
            </Button>
          )}
        </div>
        {cliente.obras.length === 0 ? (
          <p className="cliente-notas">Todavía no hay direcciones cargadas para este cliente.</p>
        ) : (
          <ul className="obras-lista">
            {cliente.obras.map((obra) => (
              <li className="obra" key={obra.id}>
                <strong>{obra.direccion}</strong>
                {obra.referencia && <span className="obra-referencia">{obra.referencia}</span>}
                {obra.notas && <p className="cliente-notas">{obra.notas}</p>}
                <div className="obra-acciones">
                  <a className="ui-btn ui-btn--secundario ui-btn--sm" href={urlMapa(obra.direccion)} target="_blank" rel="noopener noreferrer">
                    <MapPin size={18} aria-hidden="true" /> Cómo llegar
                  </a>
                  {esDueno && (
                    <>
                      <Button tamano="sm" icono={Pencil} onClick={() => setObraEnEdicion(obra)}>
                        Editar
                      </Button>
                      <Button tamano="sm" variante="peligro" icono={Trash2} onClick={() => eliminarObra(obra)}>
                        Eliminar
                      </Button>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <ClienteFormulario
        key={`c-${editando}`}
        abierto={editando}
        cliente={cliente}
        onCerrar={() => setEditando(false)}
        onGuardado={() => {
          setEditando(false)
          avisar('Cambios guardados.')
          recargar()
          alCambiar()
        }}
      />
      <ObraFormulario
        key={`o-${obraEnEdicion?.id ?? obraEnEdicion}`}
        abierto={obraEnEdicion !== null}
        clienteId={cliente.id}
        obra={obraEnEdicion === 'nueva' ? null : obraEnEdicion}
        onCerrar={() => setObraEnEdicion(null)}
        onGuardado={() => {
          avisar(obraEnEdicion === 'nueva' ? 'Obra agregada.' : 'Obra actualizada.')
          setObraEnEdicion(null)
          recargar()
          alCambiar()
        }}
      />
    </div>
  )
}
