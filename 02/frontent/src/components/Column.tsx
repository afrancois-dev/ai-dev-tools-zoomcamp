import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import type { Card, Column as ColumnModel } from '../types'
import { SortableCard } from './SortableCard'

interface ColumnProps {
  column: ColumnModel
  cards: Card[]
  onAddCard: (columnId: string) => void
  onEditCard: (card: Card) => void
}

export function Column({ column, cards, onAddCard, onEditCard }: ColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
    data: { type: 'column' },
  })

  return (
    <section className="flex w-72 shrink-0 flex-col rounded-xl bg-slate-200/70">
      <header className="flex items-center justify-between px-3 py-2.5">
        <h2 className="text-sm font-semibold text-slate-700">{column.title}</h2>
        <span className="rounded-full bg-slate-300/80 px-2 py-0.5 text-xs font-medium text-slate-600">
          {cards.length}
        </span>
      </header>

      <div
        ref={setNodeRef}
        className={`mx-2 mb-2 flex min-h-24 flex-1 flex-col gap-2 rounded-lg p-2 transition ${
          isOver ? 'bg-indigo-100/70 ring-2 ring-indigo-300' : ''
        }`}
      >
        <SortableContext
          items={cards.map((card) => card.id)}
          strategy={verticalListSortingStrategy}
        >
          {cards.map((card) => (
            <SortableCard key={card.id} card={card} onEdit={onEditCard} />
          ))}
        </SortableContext>

        {cards.length === 0 && (
          <p className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-slate-300 py-6 text-xs text-slate-400">
            Drop cards here
          </p>
        )}

        <button
          type="button"
          onClick={() => onAddCard(column.id)}
          className="mt-1 rounded-lg px-2 py-1.5 text-left text-sm font-medium text-slate-500 transition hover:bg-slate-300/60 hover:text-slate-700"
        >
          + Add card
        </button>
      </div>
    </section>
  )
}
