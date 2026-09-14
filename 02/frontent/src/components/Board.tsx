import {
  closestCorners,
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import type {
  DragEndEvent,
  DragOverEvent,
  DragStartEvent,
} from '@dnd-kit/core'
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable'
import { useRef, useState } from 'react'
import type { BoardActions } from '../hooks/useBoard'
import { cardsForColumn, isColumnId, sortColumns } from '../lib/board'
import type { Board as BoardModel, Card } from '../types'
import { AddColumn } from './AddColumn'
import { CardItem } from './CardItem'
import { CardModal } from './CardModal'
import type { CardFormValues } from './CardModal'
import { Column } from './Column'

interface BoardProps {
  board: BoardModel
  actions: BoardActions
}

type ModalState =
  | { mode: 'create'; columnId: string }
  | { mode: 'edit'; card: Card }
  | null

export function Board({ board, actions }: BoardProps) {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [modal, setModal] = useState<ModalState>(null)
  const originColumn = useRef<string | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const activeCard = activeId
    ? board.cards.find((card) => card.id === activeId) ?? null
    : null

  function resolveColumnId(overId: string): string | null {
    if (isColumnId(board, overId)) return overId
    return board.cards.find((card) => card.id === overId)?.column_id ?? null
  }

  function handleDragStart(event: DragStartEvent) {
    const cardId = String(event.active.id)
    setActiveId(cardId)
    originColumn.current =
      board.cards.find((card) => card.id === cardId)?.column_id ?? null
  }

  function handleDragOver(event: DragOverEvent) {
    const { active, over } = event
    if (!over) return

    const cardId = String(active.id)
    const overId = String(over.id)
    const card = board.cards.find((candidate) => candidate.id === cardId)
    if (!card) return

    const overColumnId = resolveColumnId(overId)
    if (!overColumnId || overColumnId === card.column_id) return

    const overCards = cardsForColumn(board.cards, overColumnId)
    const overIndex = isColumnId(board, overId)
      ? overCards.length
      : overCards.findIndex((candidate) => candidate.id === overId)

    actions.moveCardLocal(cardId, overColumnId, Math.max(0, overIndex))
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    setActiveId(null)
    originColumn.current = null
    if (!over) return

    const cardId = String(active.id)
    const overId = String(over.id)
    const card = board.cards.find((candidate) => candidate.id === cardId)
    if (!card) return

    const overColumnId = resolveColumnId(overId)
    if (!overColumnId) return

    const sameColumnReorder =
      card.column_id === overColumnId && card.column_id === originColumn.current
    const columnCards = sameColumnReorder
      ? cardsForColumn(board.cards, overColumnId)
      : cardsForColumn(board.cards, overColumnId).filter(
          (candidate) => candidate.id !== cardId,
        )

    let newIndex = columnCards.length
    if (!isColumnId(board, overId)) {
      const index = columnCards.findIndex((candidate) => candidate.id === overId)
      if (index !== -1) newIndex = index
    }

    void actions.commitCardMove(cardId, overColumnId, newIndex)
  }

  const modalColumnTitle =
    modal?.mode === 'create'
      ? board.columns.find((column) => column.id === modal.columnId)?.title
      : undefined

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={() => {
        setActiveId(null)
        originColumn.current = null
      }}
    >
      <div className="flex h-full items-start gap-4 overflow-x-auto px-6 pb-6">
        {sortColumns(board.columns).map((column) => (
          <Column
            key={column.id}
            column={column}
            cards={cardsForColumn(board.cards, column.id)}
            onAddCard={(columnId) => setModal({ mode: 'create', columnId })}
            onEditCard={(card) => setModal({ mode: 'edit', card })}
          />
        ))}

        <AddColumn onAdd={(title) => actions.addColumn(title)} />
      </div>

      <DragOverlay>
        {activeCard ? (
          <div className="w-[264px]">
            <CardItem card={activeCard} overlay />
          </div>
        ) : null}
      </DragOverlay>

      {modal?.mode === 'create' && (
        <CardModal
          mode="create"
          columnTitle={modalColumnTitle}
          onClose={() => setModal(null)}
          onSubmit={(values: CardFormValues) =>
            actions.addCard({ ...values, column_id: modal.columnId })
          }
        />
      )}

      {modal?.mode === 'edit' && (
        <CardModal
          mode="edit"
          card={modal.card}
          columnTitle={
            board.columns.find((column) => column.id === modal.card.column_id)
              ?.title
          }
          onClose={() => setModal(null)}
          onSubmit={(values) => actions.updateCard(modal.card.id, values)}
          onDelete={() => actions.deleteCard(modal.card.id)}
        />
      )}
    </DndContext>
  )
}
