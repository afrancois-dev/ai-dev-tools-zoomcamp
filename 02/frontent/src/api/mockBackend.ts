import type { Backend, CreateCardInput, MoveCardInput, UpdateCardInput } from './types'
import { cloneBoard, nextPosition } from './types'
import { moveCard as reorderCards, sortCards } from '../lib/board'
import type { Board, Card, Column, Priority } from '../types'

const DEFAULT_COLUMN_TITLES = [
  'To Do',
  'In Progress',
  'Deployed in Staging',
  'Deployed in Production',
  'On Hold',
]

/** Simulated network latency so loading/optimistic states are visible. */
const LATENCY_MS = 180

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), LATENCY_MS))
}

function seed(): Board {
  const columns: Column[] = DEFAULT_COLUMN_TITLES.map((title, order) => ({
    id: crypto.randomUUID(),
    title,
    order,
  }))

  const byTitle = (title: string) =>
    columns.find((column) => column.title === title)!.id

  const now = Date.now()
  const inDays = (days: number) =>
    new Date(now + days * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)

  const seedCards: Array<
    Pick<Card, 'title' | 'description' | 'priority' | 'due_date'> & {
      column_title: string
    }
  > = [
    {
      title: 'Define MVP scope',
      description: 'Lock down the features for the first release.',
      priority: 'High',
      due_date: inDays(3),
      column_title: 'To Do',
    },
    {
      title: 'Sketch board UI',
      description: 'Wireframe columns, cards and the drag interactions.',
      priority: 'Medium',
      due_date: inDays(5),
      column_title: 'To Do',
    },
    {
      title: 'Build drag and drop',
      description: 'Support inter-column transfer and intra-column reordering.',
      priority: 'Urgent',
      due_date: inDays(1),
      column_title: 'In Progress',
    },
    {
      title: 'Connect REST API',
      description: 'Wire the frontend to the FastAPI endpoints.',
      priority: 'Medium',
      due_date: inDays(8),
      column_title: 'In Progress',
    },
    {
      title: 'Smoke test on staging',
      description: 'Verify the five default columns load correctly.',
      priority: 'Low',
      due_date: inDays(-1),
      column_title: 'Deployed in Staging',
    },
    {
      title: 'Ship v1.0.0',
      description: 'Mini Kanban Board initial release.',
      priority: 'High',
      due_date: inDays(14),
      column_title: 'Deployed in Production',
    },
  ]

  const counters = new Map<string, number>()
  const cards: Card[] = seedCards.map((seedCard, index) => {
    const columnId = byTitle(seedCard.column_title)
    const position = counters.get(columnId) ?? 0
    counters.set(columnId, position + 1)
    return {
      id: crypto.randomUUID(),
      column_id: columnId,
      title: seedCard.title,
      description: seedCard.description,
      priority: seedCard.priority,
      created_at: new Date(now - (index + 1) * 60 * 60 * 1000).toISOString(),
      due_date: seedCard.due_date,
      position,
    }
  })

  return { columns, cards }
}

/**
 * In-memory implementation used until the FastAPI backend exists. State is
 * volatile on purpose — it resets on page reload, matching the spec's
 * "in-memory storage" backend.
 */
export function createMockBackend(): Backend {
  const state = { board: seed() }

  const flush = () => cloneBoard(state.board)

  return {
    async getBoard() {
      return delay(flush())
    },

    async createColumn(input) {
      const order =
        state.board.columns.reduce(
          (max, column) => Math.max(max, column.order),
          -1,
        ) + 1
      state.board.columns.push({
        id: crypto.randomUUID(),
        title: input.title.trim(),
        order,
      })
      return delay(flush())
    },

    async createCard(input: CreateCardInput) {
      const priority: Priority = input.priority ?? 'Medium'
      state.board.cards.push({
        id: crypto.randomUUID(),
        column_id: input.column_id,
        title: input.title.trim(),
        description: input.description?.trim() ?? '',
        priority,
        created_at: new Date().toISOString(),
        due_date: input.due_date ?? '',
        position: nextPosition(state.board.cards, input.column_id),
      })
      return delay(flush())
    },

    async updateCard(id: string, input: UpdateCardInput) {
      const card = state.board.cards.find((candidate) => candidate.id === id)
      if (!card) throw new Error(`Card ${id} not found`)
      Object.assign(card, {
        ...(input.title !== undefined && { title: input.title.trim() }),
        ...(input.description !== undefined && {
          description: input.description.trim(),
        }),
        ...(input.priority !== undefined && { priority: input.priority }),
        ...(input.due_date !== undefined && { due_date: input.due_date }),
      })
      return delay(flush())
    },

    async deleteCard(id: string) {
      const card = state.board.cards.find((candidate) => candidate.id === id)
      if (!card) throw new Error(`Card ${id} not found`)
      const columnId = card.column_id
      state.board.cards = state.board.cards.filter(
        (candidate) => candidate.id !== id,
      )
      const remaining = sortCards(
        state.board.cards.filter((candidate) => candidate.column_id === columnId),
      )
      remaining.forEach((candidate, index) => {
        candidate.position = index
      })
      return delay(flush())
    },

    async moveCard(id: string, input: MoveCardInput) {
      const card = state.board.cards.find((candidate) => candidate.id === id)
      if (!card) throw new Error(`Card ${id} not found`)
      state.board.cards = reorderCards(
        state.board.cards,
        id,
        input.column_id,
        input.position,
      )
      return delay(flush())
    },
  }
}
