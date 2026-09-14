export const PRIORITIES = ['Low', 'Medium', 'High', 'Urgent'] as const

export type Priority = (typeof PRIORITIES)[number]

export interface Column {
  id: string
  title: string
  order: number
}

export interface Card {
  id: string
  column_id: string
  title: string
  description: string
  priority: Priority
  created_at: string
  due_date: string
  position: number
}

export interface Board {
  columns: Column[]
  cards: Card[]
}
