import { Board } from './components/Board'
import { useBoard } from './hooks/useBoard'

function App() {
  const { board, loading, error, refresh, actions } = useBoard()

  return (
    <div className="flex h-full flex-col bg-slate-100">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-indigo-600 text-white">
            <BoardIcon />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-slate-800">
              KanbanLite
            </h1>
            <p className="text-xs text-slate-500">
              A lightweight single-board task workspace
            </p>
          </div>
        </div>
      </header>

      <main className="flex min-h-0 flex-1 flex-col">
        {loading && !board && <BoardSkeleton />}

        {error && (
          <div className="mx-6 mt-4 flex items-center justify-between rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <span>{error}</span>
            <button
              type="button"
              onClick={() => void refresh()}
              className="font-semibold underline"
            >
              Retry
            </button>
          </div>
        )}

        {board && (
          <div className="min-h-0 flex-1 pt-4">
            <Board board={board} actions={actions} />
          </div>
        )}
      </main>
    </div>
  )
}

function BoardIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      className="size-5"
      aria-hidden="true"
    >
      <rect x="3" y="3" width="7" height="18" rx="1.5" />
      <rect x="14" y="3" width="7" height="11" rx="1.5" />
    </svg>
  )
}

function BoardSkeleton() {
  return (
    <div className="flex gap-4 px-6 pt-4">
      {Array.from({ length: 4 }).map((_, index) => (
        <div
          key={index}
          className="h-64 w-72 shrink-0 animate-pulse rounded-xl bg-slate-200"
        />
      ))}
    </div>
  )
}

export default App
