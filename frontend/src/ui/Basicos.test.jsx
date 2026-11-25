import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import Button from './Button'
import { Input, Select, Textarea } from './Campos'
import EstadoBadge from './EstadoBadge'
import IconButton from './IconButton'
import Kpi from './Kpi'
import SearchField from './SearchField'
import Segmentado from './Segmentado'
import { iniciales } from './Avatar'

describe('Button', () => {
  it('por defecto es type=button (no envía formularios por accidente)', () => {
    render(<Button>Guardar</Button>)
    expect(screen.getByRole('button', { name: 'Guardar' })).toHaveAttribute('type', 'button')
  })

  it('cargando: queda desactivado, avisa a los lectores y no responde a clics', async () => {
    const alClic = vi.fn()
    render(<Button cargando onClick={alClic}>Guardar</Button>)
    const boton = screen.getByRole('button', { name: 'Guardar' })
    expect(boton).toBeDisabled()
    expect(boton).toHaveAttribute('aria-busy', 'true')
    await userEvent.click(boton)
    expect(alClic).not.toHaveBeenCalled()
  })

  it('el ícono es decorativo (no ensucia el nombre accesible)', () => {
    render(<Button icono={Plus}>Nuevo cliente</Button>)
    expect(screen.getByRole('button', { name: 'Nuevo cliente' })).toBeInTheDocument()
  })

  it('aplica la variante pedida', () => {
    render(<Button variante="primario">Guardar</Button>)
    expect(screen.getByRole('button')).toHaveClass('ui-btn--primario')
  })
})

describe('IconButton', () => {
  it('su nombre accesible es la etiqueta, y también se ve como ayuda', () => {
    render(<IconButton icono={Plus} etiqueta="Agregar obra" />)
    const boton = screen.getByRole('button', { name: 'Agregar obra' })
    expect(boton).toHaveAttribute('title', 'Agregar obra')
  })
})

describe('Campos', () => {
  it('la etiqueta está asociada al control', async () => {
    render(<Input etiqueta="Teléfono" />)
    await userEvent.type(screen.getByLabelText('Teléfono'), '1155')
    expect(screen.getByLabelText('Teléfono')).toHaveValue('1155')
  })

  it('la ayuda se anuncia como descripción', () => {
    render(<Input etiqueta="Usuario" ayuda="Sin tildes ni espacios" />)
    expect(screen.getByLabelText('Usuario')).toHaveAccessibleDescription('Sin tildes ni espacios')
  })

  it('un error marca el campo como inválido y se anuncia (role alert)', () => {
    render(<Input etiqueta="Teléfono" ayuda="Con código de área" error="Falta el teléfono" />)
    const campo = screen.getByLabelText('Teléfono')
    expect(campo).toHaveAttribute('aria-invalid', 'true')
    expect(campo).toHaveAccessibleDescription('Falta el teléfono')
    expect(screen.getByRole('alert')).toHaveTextContent('Falta el teléfono')
    expect(screen.queryByText('Con código de área')).toBeNull() // el error reemplaza a la ayuda
  })

  it('sin error no hay aria-invalid', () => {
    render(<Input etiqueta="Nombre" />)
    expect(screen.getByLabelText('Nombre')).not.toHaveAttribute('aria-invalid')
  })

  it('marca lo opcional con texto, no con color', () => {
    render(<Textarea etiqueta="Notas" opcional />)
    expect(screen.getByText('(opcional)')).toBeInTheDocument()
  })

  it('Select y Textarea también asocian su etiqueta', () => {
    render(
      <>
        <Select etiqueta="Tipo">
          <option>Casa</option>
        </Select>
        <Textarea etiqueta="Notas" />
      </>
    )
    expect(screen.getByLabelText('Tipo').tagName).toBe('SELECT')
    expect(screen.getByLabelText('Notas').tagName).toBe('TEXTAREA')
  })

  it('dos campos distintos nunca comparten id', () => {
    render(
      <>
        <Input etiqueta="Uno" />
        <Input etiqueta="Dos" />
      </>
    )
    expect(screen.getByLabelText('Uno').id).not.toBe(screen.getByLabelText('Dos').id)
  })
})

describe('Segmentado', () => {
  function Ejemplo({ alCambiar }) {
    const [valor, setValor] = useState('lista')
    return (
      <Segmentado
        etiqueta="Vista"
        valor={valor}
        onChange={(v) => {
          setValor(v)
          alCambiar?.(v)
        }}
        opciones={[
          { valor: 'lista', etiqueta: 'Lista' },
          { valor: 'calendario', etiqueta: 'Calendario' },
        ]}
      />
    )
  }

  it('indica la opción elegida con aria-pressed', async () => {
    render(<Ejemplo />)
    expect(screen.getByRole('button', { name: 'Lista' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Calendario' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('cambia de opción y avisa', async () => {
    const alCambiar = vi.fn()
    render(<Ejemplo alCambiar={alCambiar} />)
    await userEvent.click(screen.getByRole('button', { name: 'Calendario' }))
    expect(alCambiar).toHaveBeenCalledWith('calendario')
    expect(screen.getByRole('button', { name: 'Calendario' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('el grupo tiene nombre', () => {
    render(<Ejemplo />)
    expect(screen.getByRole('group', { name: 'Vista' })).toBeInTheDocument()
  })
})

describe('SearchField', () => {
  function Ejemplo() {
    const [valor, setValor] = useState('')
    return <SearchField etiqueta="Buscar clientes" valor={valor} onChange={setValor} />
  }

  it('es un buscador con nombre accesible', () => {
    render(<Ejemplo />)
    expect(screen.getByRole('search')).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Buscar clientes' })).toBeInTheDocument()
  })

  it('el botón de limpiar aparece solo si hay texto, y lo borra', async () => {
    render(<Ejemplo />)
    expect(screen.queryByRole('button', { name: 'Limpiar búsqueda' })).toBeNull()
    await userEvent.type(screen.getByRole('searchbox'), 'gomez')
    await userEvent.click(screen.getByRole('button', { name: 'Limpiar búsqueda' }))
    expect(screen.getByRole('searchbox')).toHaveValue('')
  })
})

describe('EstadoBadge', () => {
  it.each([
    ['trabajo', 'por_agendar', 'Por agendar'],
    ['trabajo', 'en_curso', 'En curso'],
    ['trabajo', 'cobrado', 'Cobrado'],
    ['trabajo', 'cancelado', 'Cancelado'],
    ['presupuesto', 'borrador', 'Borrador'],
    ['presupuesto', 'rechazado', 'Rechazado'],
  ])('%s %s se muestra como texto "%s" (nunca solo color)', (tipo, estado, texto) => {
    render(<EstadoBadge tipo={tipo} estado={estado} />)
    expect(screen.getByText(texto)).toBeInTheDocument()
  })

  it('cada estado de trabajo trae un ícono además del texto', () => {
    for (const estado of ['por_agendar', 'agendado', 'en_curso', 'terminado', 'cobrado', 'cancelado']) {
      const { container, unmount } = render(<EstadoBadge estado={estado} />)
      expect(container.querySelector('svg'), estado).not.toBeNull()
      unmount()
    }
  })

  it('un estado desconocido no rompe: muestra el texto tal cual', () => {
    render(<EstadoBadge estado="algo_nuevo" />)
    expect(screen.getByText('algo_nuevo')).toBeInTheDocument()
  })
})

describe('Kpi', () => {
  it('informativo: etiqueta y valor, sin botón', () => {
    render(<Kpi etiqueta="Falta cobrar" valor="$ 4.413.000" />)
    expect(screen.getByText('Falta cobrar')).toBeInTheDocument()
    expect(screen.getByText('$ 4.413.000')).toBeInTheDocument()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('con onClick es un botón que lleva a algún lado', async () => {
    const alClic = vi.fn()
    render(<Kpi etiqueta="Por agendar" valor="3" onClick={alClic} />)
    await userEvent.click(screen.getByRole('button', { name: /Por agendar/ }))
    expect(alClic).toHaveBeenCalled()
  })
})

describe('iniciales', () => {
  it.each([
    ['Ana María Pérez', 'AP'],
    ['Dora', 'D'],
    ['  juan   gómez ', 'JG'],
    ['', '?'],
  ])('"%s" -> %s', (nombre, esperado) => {
    expect(iniciales(nombre)).toBe(esperado)
  })
})
