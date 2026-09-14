import type {
  Backend,
  CreateCardInput,
  CreateColumnInput,
  MoveCardInput,
  UpdateCardInput,
} from './types'
import type { Board } from '../types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    throw new Error(`Request failed (${response.status}) for ${path}`)
  }
  return (await response.json()) as T
}

/**
 * Real FastAPI backend implementation. State-changing endpoints return the full
 * board so the caller can replace local state in one step. Not used yet —
 * `boardApi` still points at the mock backend.
 */
export const httpBackend: Backend = {
  getBoard: () => request<Board>('/board'),

  createColumn: (input: CreateColumnInput) =>
    request<Board>('/columns', {
      method: 'POST',
      body: JSON.stringify(input),
    }),

  createCard: (input: CreateCardInput) =>
    request<Board>('/cards', {
      method: 'POST',
      body: JSON.stringify(input),
    }),

  updateCard: (id: string, input: UpdateCardInput) =>
    request<Board>(`/cards/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(input),
    }),

  deleteCard: (id: string) =>
    request<Board>(`/cards/${id}`, { method: 'DELETE' }),

  moveCard: (id: string, input: MoveCardInput) =>
    request<Board>(`/cards/${id}/move`, {
      method: 'PATCH',
      body: JSON.stringify(input),
    }),
}
