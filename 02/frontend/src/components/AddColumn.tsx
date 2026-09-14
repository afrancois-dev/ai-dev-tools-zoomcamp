import { useState } from 'react'
import type { FormEvent } from 'react'

interface AddColumnProps {
  onAdd: (title: string) => Promise<void>
}

export function AddColumn({ onAdd }: AddColumnProps) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const value = title.trim()
    if (!value || submitting) return
    setSubmitting(true)
    try {
      await onAdd(value)
      setTitle('')
      setOpen(false)
    } finally {
      setSubmitting(false)
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="w-72 shrink-0 rounded-xl border border-dashed border-slate-300 bg-slate-100/60 px-4 py-3 text-left text-sm font-medium text-slate-500 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-600"
      >
        + Add column
      </button>
    )
  }

  return (
    <form
      onSubmit={submit}
      className="flex w-72 shrink-0 flex-col gap-2 rounded-xl bg-slate-200/70 p-3"
    >
      <input
        autoFocus
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            setOpen(false)
            setTitle('')
          }
        }}
        placeholder="Column title"
        className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
      />
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={!title.trim() || submitting}
          className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
        >
          Add
        </button>
        <button
          type="button"
          onClick={() => {
            setOpen(false)
            setTitle('')
          }}
          className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-300/60"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
