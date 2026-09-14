import type { Priority } from '../types'

const STYLES: Record<Priority, string> = {
  Low: 'bg-slate-100 text-slate-600 ring-slate-200',
  Medium: 'bg-sky-100 text-sky-700 ring-sky-200',
  High: 'bg-amber-100 text-amber-700 ring-amber-200',
  Urgent: 'bg-red-100 text-red-700 ring-red-200',
}

const DOTS: Record<Priority, string> = {
  Low: 'bg-slate-400',
  Medium: 'bg-sky-500',
  High: 'bg-amber-500',
  Urgent: 'bg-red-500',
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STYLES[priority]}`}
    >
      <span className={`size-1.5 rounded-full ${DOTS[priority]}`} />
      {priority}
    </span>
  )
}
