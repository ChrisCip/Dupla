import { Plus } from 'lucide-react'

import { hueClassForUuid, userDisplayInitials } from '../lib/taskboard'
import type { TaskAssigneeOption } from '../types/taskBoard'
import { PrimaryButton } from './PrimaryButton'

type TaskboardToolbarProps = {
  embedded: boolean
  showAddTask: boolean
  onAddTask: () => void
  boardSearch: string
  setBoardSearch: React.Dispatch<React.SetStateAction<string>>
  mineOnly: boolean
  setMineOnly: React.Dispatch<React.SetStateAction<boolean>>
  filterAssignee: string
  setFilterAssignee: React.Dispatch<React.SetStateAction<string>>
  includeArchived: boolean
  setIncludeArchived: React.Dispatch<React.SetStateAction<boolean>>
  assignees: TaskAssigneeOption[]
  todosSelected: boolean
}

export function TaskboardToolbar({
  embedded,
  showAddTask,
  onAddTask,
  boardSearch,
  setBoardSearch,
  mineOnly,
  setMineOnly,
  filterAssignee,
  setFilterAssignee,
  includeArchived,
  setIncludeArchived,
  assignees,
  todosSelected,
}: TaskboardToolbarProps) {
  return (
    <div
      className={`flex shrink-0 flex-col gap-2 rounded-lg border border-black/8 bg-white px-2 py-2 shadow-sm sm:flex-row sm:items-center sm:gap-3 sm:px-3 ${embedded ? '' : 'gap-3 px-3 py-3 sm:gap-4 sm:px-4'}`}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-2 sm:max-w-none sm:flex-row sm:items-center sm:gap-2">
        <div className="relative min-w-0 flex-1 sm:max-w-sm">
        <svg
          className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.75}
          stroke="currentColor"
          aria-hidden
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
          />
        </svg>
        <input
          type="search"
          value={boardSearch}
          onChange={(e) => setBoardSearch(e.target.value)}
          placeholder="Buscar en el tablero"
          className="du-input h-9 w-full rounded-md border-black/10 bg-white py-0 pl-9 pr-3 text-sm placeholder:text-muted/90 focus:border-primary/35 focus:ring-1 focus:ring-primary/25"
          aria-label="Buscar en el tablero"
        />
        </div>
        {showAddTask ? (
          <PrimaryButton
            type="button"
            className="h-9 shrink-0 gap-1.5 px-3 py-0 text-xs font-semibold normal-case tracking-normal"
            onClick={onAddTask}
          >
            <Plus className="h-3.5 w-3.5 shrink-0" strokeWidth={2.5} aria-hidden />
            Añadir tarea
          </PrimaryButton>
        ) : null}
      </div>

      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2 sm:justify-end sm:gap-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            aria-pressed={mineOnly}
            onClick={() => {
              setMineOnly((prev) => {
                if (!prev) setFilterAssignee('')
                return !prev
              })
            }}
            className={`rounded-full border px-2.5 py-1 text-xs font-medium transition ${
              mineOnly
                ? 'border-primary/35 bg-primary/12 text-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]'
                : 'border-black/10 bg-white text-ink hover:border-black/18 hover:bg-black/[0.03]'
            }`}
          >
            Mis tareas
          </button>
          <button
            type="button"
            aria-pressed={includeArchived}
            onClick={() => setIncludeArchived((v) => !v)}
            className={`rounded-full border px-2.5 py-1 text-xs font-medium transition ${
              includeArchived
                ? 'border-primary/35 bg-primary/12 text-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]'
                : 'border-black/10 bg-white text-ink hover:border-black/18 hover:bg-black/[0.03]'
            }`}
          >
            Archivadas
          </button>
        </div>

        <div className="hidden h-7 w-px shrink-0 bg-black/10 sm:block" />

        <div className="flex min-w-0 items-center gap-2">
          <span className="shrink-0 self-center text-[10px] font-semibold uppercase tracking-wider text-muted">
            Equipo
          </span>
          <div
            className="min-w-0 max-w-[min(100vw-2rem,28rem)] sm:max-w-none"
            role="group"
            aria-label="Filtrar por persona asignada"
          >
            <div className="flex max-w-full items-center gap-0 overflow-x-auto py-1 [scrollbar-width:thin]">
              <div className="flex items-center -space-x-1.5 pr-1">
                <span
                  className={`relative z-10 inline-flex h-8 w-8 shrink-0 rounded-full p-[2px] ${
                    todosSelected ? 'bg-primary' : 'bg-white shadow-[0_0_0_1px_rgba(0,0,0,.06)]'
                  }`}
                >
                  {todosSelected ? (
                    <span className="flex min-h-0 min-w-0 flex-1 rounded-full bg-white p-[2px]">
                      <button
                        type="button"
                        title="Todos los asignados"
                        disabled={mineOnly}
                        onClick={() => {
                          setFilterAssignee('')
                          setMineOnly(false)
                        }}
                        className={`flex flex-1 items-center justify-center rounded-full bg-neutral-700 text-white transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
                          mineOnly ? 'cursor-not-allowed opacity-40' : ''
                        }`}
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 24 24"
                          fill="none"
                          className="h-3.5 w-3.5"
                          stroke="currentColor"
                          strokeWidth={2}
                          aria-hidden
                        >
                          <rect x="3" y="3" width="7" height="7" rx="1" />
                          <rect x="14" y="3" width="7" height="7" rx="1" />
                          <rect x="3" y="14" width="7" height="7" rx="1" />
                          <rect x="14" y="14" width="7" height="7" rx="1" />
                        </svg>
                      </button>
                    </span>
                  ) : (
                    <button
                      type="button"
                      title="Todos los asignados"
                      disabled={mineOnly}
                      onClick={() => {
                        setFilterAssignee('')
                        setMineOnly(false)
                      }}
                      className={`flex h-full w-full items-center justify-center rounded-full text-white transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
                        mineOnly ? 'cursor-not-allowed opacity-40' : 'bg-neutral-400 hover:bg-neutral-500'
                      }`}
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="none"
                        className="h-3.5 w-3.5"
                        stroke="currentColor"
                        strokeWidth={2}
                        aria-hidden
                      >
                        <rect x="3" y="3" width="7" height="7" rx="1" />
                        <rect x="14" y="3" width="7" height="7" rx="1" />
                        <rect x="3" y="14" width="7" height="7" rx="1" />
                        <rect x="14" y="14" width="7" height="7" rx="1" />
                      </svg>
                    </button>
                  )}
                </span>
                {assignees.map((a, i) => {
                  const selected = !mineOnly && filterAssignee === a.uuid
                  return (
                    <span
                      key={a.uuid}
                      className={`relative inline-flex h-8 w-8 shrink-0 rounded-full p-[2px] ${
                        selected ? 'bg-primary' : 'bg-white shadow-[0_0_0_1px_rgba(0,0,0,.06)]'
                      }`}
                      style={{ zIndex: 20 + i }}
                    >
                      {selected ? (
                        <span className="flex min-h-0 min-w-0 flex-1 rounded-full bg-white p-[2px]">
                          <button
                            type="button"
                            title={a.email}
                            disabled={mineOnly}
                            onClick={() => {
                              setMineOnly(false)
                              setFilterAssignee(a.uuid)
                            }}
                            className={`flex flex-1 items-center justify-center rounded-full text-[10px] font-semibold uppercase text-white transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${hueClassForUuid(a.uuid)} ${
                              mineOnly ? 'cursor-not-allowed opacity-40' : ''
                            }`}
                          >
                            {userDisplayInitials(a.first_name, a.last_name, a.email)}
                          </button>
                        </span>
                      ) : (
                        <button
                          type="button"
                          title={a.email}
                          disabled={mineOnly}
                          onClick={() => {
                            setMineOnly(false)
                            setFilterAssignee(a.uuid)
                          }}
                          className={`flex h-full w-full items-center justify-center rounded-full text-[10px] font-semibold uppercase text-white transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${hueClassForUuid(a.uuid)} hover:brightness-110 ${
                            mineOnly ? 'cursor-not-allowed opacity-40' : ''
                          }`}
                        >
                          {userDisplayInitials(a.first_name, a.last_name, a.email)}
                        </button>
                      )}
                    </span>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
