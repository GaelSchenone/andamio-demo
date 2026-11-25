import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Con globals apagado, Testing Library no limpia el DOM sola entre tests.
afterEach(() => cleanup())
