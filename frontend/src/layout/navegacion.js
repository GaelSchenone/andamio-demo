import { FileText, HardHat, House, Settings, Users, Wallet } from 'lucide-react'

// Lo que ve cada rol. El servidor igual vuelve a controlar los permisos en cada pedido: esto solo
// evita mostrar pantallas que darían "no tenés permiso". Las rutas prohibidas redirigen a Inicio.
const INICIO = { ruta: '/', etiqueta: 'Inicio', icono: House, fin: true }
const TRABAJOS = { ruta: '/trabajos', etiqueta: 'Trabajos', icono: HardHat }
const PRESUPUESTOS = { ruta: '/presupuestos', etiqueta: 'Presupuestos', icono: FileText }
const COBROS = { ruta: '/cobros', etiqueta: 'Cobros', icono: Wallet }
const CLIENTES = { ruta: '/clientes', etiqueta: 'Clientes', icono: Users }
const AJUSTES = { ruta: '/ajustes', etiqueta: 'Ajustes', icono: Settings }

export const GRUPOS_POR_ROL = {
  dueno: [
    { titulo: null, items: [INICIO] },
    { titulo: 'Operación', items: [PRESUPUESTOS, TRABAJOS, COBROS] },
    { titulo: 'Contactos', items: [CLIENTES] },
    { titulo: 'Sistema', items: [AJUSTES] },
  ],
  empleado: [
    { titulo: null, items: [INICIO] },
    { titulo: 'Operación', items: [TRABAJOS] },
    { titulo: 'Contactos', items: [CLIENTES] },
    { titulo: 'Sistema', items: [AJUSTES] },
  ],
}

// Barra inferior del celular: lo más usado en obra, y "Más" con el resto (solo si hace falta).
export const BARRA_INFERIOR_POR_ROL = {
  dueno: { principales: [INICIO, PRESUPUESTOS, TRABAJOS, COBROS], mas: [CLIENTES, AJUSTES] },
  empleado: { principales: [INICIO, TRABAJOS, CLIENTES, AJUSTES], mas: [] },
}

export const rutasPermitidas = (rol) =>
  GRUPOS_POR_ROL[rol].flatMap((g) => g.items.map((i) => i.ruta))

