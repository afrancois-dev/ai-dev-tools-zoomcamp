import { createMockBackend } from './mockBackend'
import { httpBackend } from './httpBackend'
import type { Backend } from './types'

export type {
  Backend,
  CreateCardInput,
  CreateColumnInput,
  MoveCardInput,
  UpdateCardInput,
} from './types'

/**
 * Single entry point for every backend call in the app.
 *
 * The UI only ever imports `boardApi`, never `fetch` or a concrete backend.
 * Flip `USE_MOCK` to `false` (or set `VITE_API_BASE_URL`) once the FastAPI
 * backend is running and the same calls hit real HTTP endpoints.
 */
const USE_MOCK = true

export const boardApi: Backend = USE_MOCK
  ? createMockBackend()
  : httpBackend
