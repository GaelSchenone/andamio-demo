import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '../styles/fuentes.css'
import '../styles/tokens.css'
import '../styles/base.css'
import Galeria from './Galeria'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Galeria />
  </StrictMode>
)
