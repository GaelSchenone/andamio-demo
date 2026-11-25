import { useEffect, useMemo, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { api } from './api'
import AppShell from './layout/AppShell'
import { SesionContexto } from './layout/sesion'
import Ajustes from './pages/Ajustes/Ajustes'
import Clientes from './pages/Clientes/Clientes'
import Cobros from './pages/Cobros/Cobros'
import Inicio from './pages/Inicio/Inicio'
import Login from './pages/Login'
import EditorPresupuesto from './pages/Presupuestos/EditorPresupuesto'
import Presupuestos from './pages/Presupuestos/Presupuestos'
import Trabajos from './pages/Trabajos/Trabajos'
import { ConfirmarProvider, Skeleton, ToastProvider } from './ui'

// Las rutas de plata y presupuestos son solo del dueño. El servidor igual vuelve a controlar los
// permisos en cada pedido: esto solo evita mostrar pantallas que darían "no tenés permiso".
function SoloDueno({ esDueno, children }) {
  return esDueno ? children : <Navigate to="/" replace />
}

export default function App() {
  const [verificando, setVerificando] = useState(true)
  const [yo, setYo] = useState(null)

  useEffect(() => {
    api
      .yo()
      .then(setYo)
      .catch(() => setYo(null))
      .finally(() => setVerificando(false))
  }, [])

  const sesion = useMemo(() => (yo ? { yo, esDueno: yo.rol === 'dueno' } : null), [yo])

  async function salir() {
    await api.logout().catch(() => {})
    setYo(null)
  }

  if (verificando) {
    return (
      <div className="app-cargando" aria-busy="true">
        <Skeleton alto="2rem" ancho="12rem" />
      </div>
    )
  }

  return (
    <ToastProvider>
      <ConfirmarProvider>
        {!sesion ? (
          <Login onIngresar={setYo} />
        ) : (
          <SesionContexto.Provider value={sesion}>
            <BrowserRouter>
              <Routes>
                <Route element={<AppShell onSalir={salir} />}>
                  <Route index element={<Inicio />} />
                  <Route path="trabajos/:id?" element={<Trabajos />} />
                  <Route path="clientes/:id?" element={<Clientes />} />
                  <Route path="ajustes/:seccion?" element={<Ajustes />} />
                  <Route path="presupuestos" element={<SoloDueno esDueno={sesion.esDueno}><Presupuestos /></SoloDueno>} />
                  <Route path="presupuestos/nuevo" element={<SoloDueno esDueno={sesion.esDueno}><EditorPresupuesto /></SoloDueno>} />
                  <Route path="presupuestos/:id/editar" element={<SoloDueno esDueno={sesion.esDueno}><EditorPresupuesto /></SoloDueno>} />
                  <Route path="presupuestos/:id" element={<SoloDueno esDueno={sesion.esDueno}><Presupuestos /></SoloDueno>} />
                  <Route path="cobros/:trabajoId?" element={<SoloDueno esDueno={sesion.esDueno}><Cobros /></SoloDueno>} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
              </Routes>
            </BrowserRouter>
          </SesionContexto.Provider>
        )}
      </ConfirmarProvider>
    </ToastProvider>
  )
}
