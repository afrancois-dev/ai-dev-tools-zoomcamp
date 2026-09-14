import type { Board, Card, Priority } from '../types'

export interface CreateColumnInput {
  title: string
}

export interface CreateCardInput {
  column_id: string
  title: string
  description?: string
  priority?: Priority
  due_date?: string
}

export interface UpdateCardInput {
  title?: string
  description?: string
  priority?: Priority
  due_date?: string
}

export interface MoveCardInput {
  column_id: string
  position: number
}

/**
 * The contract every backend implementation must satisfy. Keeping it explicit
 * means the mocked backend and the real HTTP backend are interchangeable.
 */
export interface Backend {
  getBoard(): Promise<Board>
  createColumn(input: CreateColumnInput): Promise<Board>
  createCard(input: CreateCardInput): Promise<Board>
  updateCard(id: string, input: UpdateCardInput): Promise<Board>
  deleteCard(id: string): Promise<Board>
  moveCard(id: string, input: MoveCardInput): Promise<Board>
}

export function cloneBoard(board: Board): Board {
  return structuredClone(board)
}

export function nextPosition(cards: Card[], columnId: string): number {
  return cards.filter((card) => card.column_id === columnId).length
}
