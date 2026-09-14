import { useCallback, useEffect, useRef, useState } from 'react'
import { boardApi } from '../api'
import type {
  CreateCardInput,
  UpdateCardInput,
} from '../api'
import { moveCard } from '../lib/board'
import type { Board } from '../types'

export interface BoardActions {
  addColumn(title: string): Promise<void>
  addCard(input: CreateCardInput): Promise<void>
  updateCard(id: string, input: UpdateCardInput): Promise<void>
  deleteCard(id: string): Promise<void>
  /** Optimistic-only move used while dragging (no network request). */
  moveCardLocal(cardId: string, toColumnId: string, toIndex: number): void
  /** Persist a move; applies optimistically and reconciles with the backend. */
  commitCardMove(cardId: string, toColumnId: string, toIndex: number): Promise<void>
}

export interface UseBoardResult {
  board: Board | null
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
  actions: BoardActions
}

export function useBoard(): UseBoardResult {
  const [board, setBoard] = useState<Board | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const requested = useRef(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      setBoard(await boardApi.getBoard())
      setError(null)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Failed to load board')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (requested.current) return
    requested.current = true
    void refresh()
  }, [refresh])

  const run = useCallback(
    async (call: () => Promise<Board>) => {
      try {
        setBoard(await call())
        setError(null)
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'Something went wrong')
        throw cause
      }
    },
    [],
  )

  const actions: BoardActions = {
    addColumn: (title) => run(() => boardApi.createColumn({ title })),
    addCard: (input) => run(() => boardApi.createCard(input)),
    updateCard: (id, input) => run(() => boardApi.updateCard(id, input)),
    deleteCard: (id) => run(() => boardApi.deleteCard(id)),

    moveCardLocal: (cardId, toColumnId, toIndex) => {
      setBoard((current) =>
        current
          ? { ...current, cards: moveCard(current.cards, cardId, toColumnId, toIndex) }
          : current,
      )
    },

    commitCardMove: async (cardId, toColumnId, toIndex) => {
      setBoard((current) =>
        current
          ? { ...current, cards: moveCard(current.cards, cardId, toColumnId, toIndex) }
          : current,
      )
      try {
        const next = await boardApi.moveCard(cardId, {
          column_id: toColumnId,
          position: toIndex,
        })
        setBoard(next)
        setError(null)
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'Failed to move card')
        await refresh()
      }
    },
  }

  return { board, loading, error, refresh, actions }
}
