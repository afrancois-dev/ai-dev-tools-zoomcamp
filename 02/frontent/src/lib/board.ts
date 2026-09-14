import type { Board, Card, Column } from '../types'

export function sortColumns(columns: Column[]): Column[] {
  return [...columns].sort((a, b) => a.order - b.order)
}

export function sortCards(cards: Card[]): Card[] {
  return [...cards].sort(
    (a, b) =>
      a.position - b.position || a.created_at.localeCompare(b.created_at),
  )
}

export function cardsForColumn(cards: Card[], columnId: string): Card[] {
  return sortCards(cards.filter((card) => card.column_id === columnId))
}

export function isColumnId(board: Board, id: string): boolean {
  return board.columns.some((column) => column.id === id)
}

/**
 * Move a card to `toIndex` within `toColumnId`, returning a new card array with
 * positions re-normalized for both the source and destination columns.
 * Pure helper shared by the mocked backend and the optimistic UI.
 */
export function moveCard(
  cards: Card[],
  cardId: string,
  toColumnId: string,
  toIndex: number,
): Card[] {
  const card = cards.find((candidate) => candidate.id === cardId)
  if (!card) return cards

  const fromColumnId = card.column_id
  const remaining = cards.filter((candidate) => candidate.id !== cardId)

  const target = sortCards(
    remaining.filter((candidate) => candidate.column_id === toColumnId),
  )
  const clampedIndex = Math.max(0, Math.min(toIndex, target.length))
  target.splice(clampedIndex, 0, { ...card, column_id: toColumnId })

  const targetPositions = new Map(
    target.map((candidate, index) => [candidate.id, index]),
  )
  const sourcePositions =
    fromColumnId === toColumnId
      ? new Map<string, number>()
      : new Map(
          sortCards(
            remaining.filter(
              (candidate) => candidate.column_id === fromColumnId,
            ),
          ).map((candidate, index) => [candidate.id, index]),
        )

  return cards.map((candidate) => {
    if (targetPositions.has(candidate.id)) {
      return {
        ...candidate,
        column_id: toColumnId,
        position: targetPositions.get(candidate.id)!,
      }
    }
    if (sourcePositions.has(candidate.id)) {
      return { ...candidate, position: sourcePositions.get(candidate.id)! }
    }
    return candidate
  })
}
