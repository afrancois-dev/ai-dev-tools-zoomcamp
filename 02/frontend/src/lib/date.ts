export function formatDate(value: string): string {
  if (!value) return ''
  const date = new Date(value.length <= 10 ? `${value}T00:00:00` : value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function isOverdue(value: string): boolean {
  if (!value) return false
  const due = new Date(value.length <= 10 ? `${value}T23:59:59` : value)
  return due.getTime() < Date.now()
}

export function todayISO(): string {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60 * 1000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}
