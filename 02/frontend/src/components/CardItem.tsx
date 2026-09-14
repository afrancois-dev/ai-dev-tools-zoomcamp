import { formatDate, isOverdue } from '../lib/date'
import type { Card } from '../types'
import { PriorityBadge } from './PriorityBadge'

interface CardItemProps {
  card: Card
  onEdit?: (card: Card) => void
  overlay?: boolean
}

export function CardItem({ card, onEdit, overlay = false }: CardItemProps) {
  const overdue = card.due_date ? isOverdue(card.due_date) : false

  return (
    <article
      onClick={onEdit ? () => onEdit(card) : undefined}
      className={`group rounded-lg border border-slate-200 bg-white p-3 text-left shadow-sm transition ${
        overlay
          ? 'rotate-2 cursor-grabbing shadow-lg ring-2 ring-indigo-400'
          : 'cursor-grab hover:border-indigo-300 hover:shadow-md active:cursor-grabbing'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-800">{card.title}</h3>
        <PriorityBadge priority={card.priority} />
      </div>

      {card.description && (
        <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-slate-500">
          {card.description}
        </p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
        {card.due_date && (
          <span
            className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-medium ${
              overdue
                ? 'bg-red-50 text-red-600'
                : 'bg-slate-50 text-slate-500'
            }`}
          >
            <CalendarIcon />
            {overdue ? 'Overdue' : 'Due'} {formatDate(card.due_date)}
          </span>
        )}
        <span className="ml-auto">
          Created {formatDate(card.created_at)}
        </span>
      </div>
    </article>
  )
}

function CalendarIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="size-3"
      aria-hidden="true"
    >
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
    </svg>
  )
}
