import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { PrimaryButton } from './PrimaryButton'
import { TaskboardCardModal } from './TaskboardCardModal'
import { TaskboardCreateModal } from './TaskboardCreateModal'
import { WORKFLOW_PHASE_LABELS } from '../constants/workflowPhases'
import { useAuthStore } from '../store/authStore'
import type { TaskAssigneeOption, TaskBoardDto, TaskCardDto, TaskListDto } from '../types/taskBoard'

function labelForCreatedPhase(phase: string | null | undefined): string | null {
  if (!phase) return null
  return WORKFLOW_PHASE_LABELS[phase] ?? phase
}

const CARD_MIME = 'application/x-dupla-task-card'

const AVATAR_RING = [
  'bg-emerald-600',
  'bg-sky-600',
  'bg-amber-600',
  'bg-violet-600',
  'bg-rose-600',
  'bg-cyan-600',
  'bg-fuchsia-600',
  'bg-lime-700',
]

function emailInitials(email: string): string {
  const local = email.split('@')[0] ?? email
  const parts = local.split(/[._\-+]+/).filter(Boolean)
  if (parts.length >= 2) {
    return (parts[0]!.charAt(0) + parts[1]!.charAt(0)).toUpperCase().slice(0, 2)
  }
  return local.slice(0, 2).toUpperCase() || '?'
}

function hueClassForUuid(uuid: string): string {
  let h = 0
  for (let i = 0; i < uuid.length; i += 1) h = (h + uuid.charCodeAt(i) * (i + 1)) % 997
  return AVATAR_RING[h % AVATAR_RING.length]!
}

function cardMatchesSearch(card: TaskCardDto, needle: string): boolean {
  if (!needle) return true
  const t = card.title.toLowerCase()
  const d = (card.description ?? '').toLowerCase()
  const a = (card.assignee_email ?? '').toLowerCase()
  const c = (card.creator_email ?? '').toLowerCase()
  const ph = labelForCreatedPhase(card.created_in_phase)?.toLowerCase() ?? ''
  return (
    t.includes(needle) ||
    d.includes(needle) ||
    a.includes(needle) ||
    c.includes(needle) ||
    ph.includes(needle)
  )
}

function boardQueryParams(
  mine: boolean,
  assigneeUuid: string,
  includeArchived: boolean,
  projectUuid: string,
): string {
  const p = new URLSearchParams()
  if (includeArchived) p.set('include_archived', 'true')
  if (mine) p.set('mine', 'true')
  else if (assigneeUuid) p.set('assignee_uuid', assigneeUuid)
  if (projectUuid) p.set('project_uuid', projectUuid)
  const s = p.toString()
  return s ? `?${s}` : ''
}

export type TaskboardViewProps = {
  /** Filtro fijo por proyecto; vacío = tablero global */
  projectUuid?: string
  variant: 'full' | 'embedded'
}

export function TaskboardView({ projectUuid: projectFilter = '', variant }: TaskboardViewProps) {
  const token = useAuthStore((s) => s.token)
  const [board, setBoard] = useState<TaskBoardDto | null>(null)
  const [assignees, setAssignees] = useState<TaskAssigneeOption[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [includeArchived, setIncludeArchived] = useState(false)
  const [mineOnly, setMineOnly] = useState(false)
  const [filterAssignee, setFilterAssignee] = useState('')
  const [boardSearch, setBoardSearch] = useState('')
  const [modalCard, setModalCard] = useState<TaskCardDto | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const dragRef = useRef(false)

  const assigneeProjectScope = useMemo(
    () => projectFilter || modalCard?.project_uuid || '',
    [projectFilter, modalCard?.project_uuid],
  )

  const load = useCallback(async () => {
    if (!token) return
    setError(null)
    const qs = boardQueryParams(mineOnly, filterAssignee, includeArchived, projectFilter)
    const res = await apiFetch(`/api/tasks/board${qs}`, { token })
    if (!res.ok) {
      setError('No se pudo cargar el tablero')
      setBoard(null)
      return
    }
    setBoard((await res.json()) as TaskBoardDto)
  }, [token, mineOnly, filterAssignee, includeArchived, projectFilter])

  const loadAssignees = useCallback(async () => {
    if (!token) return
    const qs = assigneeProjectScope
      ? `?project_uuid=${encodeURIComponent(assigneeProjectScope)}`
      : ''
    const res = await apiFetch(`/api/tasks/assignees${qs}`, { token })
    if (!res.ok) return
    setAssignees((await res.json()) as TaskAssigneeOption[])
  }, [token, assigneeProjectScope])

  useEffect(() => {
    void loadAssignees()
  }, [loadAssignees])

  useEffect(() => {
    let cancelled = false
    async function run() {
      setLoading(true)
      await load()
      if (!cancelled) setLoading(false)
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [load])

  async function moveCard(cardUuid: string, listUuid: string, position: number) {
    if (!token) return
    const res = await apiFetch(`/api/tasks/cards/${cardUuid}`, {
      method: 'PATCH',
      token,
      body: JSON.stringify({ list_uuid: listUuid, position }),
    })
    if (!res.ok) return
    await load()
  }

  function onDragEnd() {
    window.setTimeout(() => {
      dragRef.current = false
    }, 0)
  }

  function onDragStartCard(e: React.DragEvent, cardUuid: string) {
    dragRef.current = true
    e.dataTransfer.setData(CARD_MIME, cardUuid)
    e.dataTransfer.effectAllowed = 'move'
  }

  function onDragOver(e: React.DragEvent) {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  function sortedCards(list: TaskListDto): TaskCardDto[] {
    return [...list.cards].sort((a, b) => a.position - b.position || a.uuid.localeCompare(b.uuid))
  }

  function onDropOnColumn(e: React.DragEvent, list: TaskListDto) {
    e.preventDefault()
    const cardUuid = e.dataTransfer.getData(CARD_MIME)
    if (!cardUuid) return
    const without = sortedCards(list).filter((c) => c.uuid !== cardUuid)
    void moveCard(cardUuid, list.uuid, without.length)
  }

  function onDropOnCard(e: React.DragEvent, list: TaskListDto, insertIndex: number) {
    e.preventDefault()
    e.stopPropagation()
    const cardUuid = e.dataTransfer.getData(CARD_MIME)
    if (!cardUuid) return
    const sorted = sortedCards(list)
    const target = sorted[insertIndex]
    if (!target || target.uuid === cardUuid) return
    const without = sorted.filter((c) => c.uuid !== cardUuid)
    const pos = without.findIndex((c) => c.uuid === target.uuid)
    if (pos < 0) return
    void moveCard(cardUuid, list.uuid, pos)
  }

  function openCard(card: TaskCardDto) {
    if (dragRef.current) return
    setModalCard(card)
  }

  const lists = useMemo((): TaskListDto[] => {
    if (!board) return []
    return [...board.lists].sort((a, b) => a.position - b.position || a.uuid.localeCompare(b.uuid))
  }, [board])

  const searchNeedle = boardSearch.trim().toLowerCase()

  const displayLists = useMemo(() => {
    if (!searchNeedle) return lists
    return lists.map((list) => ({
      ...list,
      cards: list.cards.filter((c) => cardMatchesSearch(c, searchNeedle)),
    }))
  }, [lists, searchNeedle])

  const displayArchivedCards = useMemo(() => {
    if (!board) return []
    if (!searchNeedle) return board.archived_cards
    return board.archived_cards.filter((c) => cardMatchesSearch(c, searchNeedle))
  }, [board, searchNeedle])

  const listOptions = lists.map((l) => ({ uuid: l.uuid, title: l.title }))

  const todosSelected = !mineOnly && filterAssignee === ''

  const embedded = variant === 'embedded'

  return (
    <div className={`flex min-h-0 flex-1 flex-col ${embedded ? 'gap-2 overflow-hidden' : 'gap-4'}`}>
      {!embedded ? (
        <div className="flex shrink-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-ink">Tablero de tareas</h1>
            <p className="mt-2 text-sm text-muted">
              Asigna personas, descripciones breves y archiva lo completado. Clic en una tarjeta para el detalle.
            </p>
            {projectFilter ? (
              <p className="mt-2 text-sm text-ink">
                Filtrando por proyecto.{' '}
                <Link className="font-semibold text-primary underline-offset-2 hover:underline" to="/app/tasks">
                  Ver tablero global
                </Link>{' '}
                ·{' '}
                <Link
                  className="font-semibold text-primary underline-offset-2 hover:underline"
                  to={`/app/projects/${projectFilter}`}
                >
                  Volver al workspace
                </Link>
              </p>
            ) : null}
          </div>
          {board ? (
            <PrimaryButton type="button" className="shrink-0 self-start" onClick={() => setCreateOpen(true)}>
              Añadir tarea
            </PrimaryButton>
          ) : null}
        </div>
      ) : (
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-ink">Tareas del proyecto</h2>
          {board ? (
            <PrimaryButton type="button" className="shrink-0 py-1.5 text-sm" onClick={() => setCreateOpen(true)}>
              Añadir tarea
            </PrimaryButton>
          ) : null}
        </div>
      )}

      {loading ? (
        <p className="min-h-0 flex-1 text-sm text-muted">Cargando tablero…</p>
      ) : error || !board ? (
        <p className="text-sm text-primary">{error ?? 'Sin datos'}</p>
      ) : (
        <>
          <div
            className={`flex shrink-0 flex-col gap-2 rounded-lg border border-black/8 bg-white px-2 py-2 shadow-sm sm:flex-row sm:items-center sm:gap-3 sm:px-3 ${embedded ? '' : 'gap-3 px-3 py-3 sm:gap-4 sm:px-4'}`}
          >
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
                className="du-input w-full rounded-md border-black/10 bg-white py-1.5 pl-9 pr-3 text-sm placeholder:text-muted/90 focus:border-primary/35 focus:ring-1 focus:ring-primary/25"
                aria-label="Buscar en el tablero"
              />
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
                          todosSelected
                            ? 'bg-primary'
                            : 'bg-white shadow-[0_0_0_1px_rgba(0,0,0,.06)]'
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
                                  {emailInitials(a.email)}
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
                                {emailInitials(a.email)}
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

          <div
            className={`flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-black/10 bg-black/2 shadow-[var(--shadow-card)] ${embedded ? 'min-h-[12rem]' : ''}`}
          >
            <div
              className={
                embedded
                  ? 'min-h-0 flex-1 overflow-x-auto overflow-y-hidden p-2'
                  : 'min-h-0 flex-1 overflow-x-auto overflow-y-hidden p-2 md:overflow-x-hidden'
              }
            >
              <div
                className={
                  embedded
                    ? 'flex h-full min-h-[10rem] w-max min-w-full items-stretch gap-2 sm:gap-3'
                    : 'flex h-full min-h-0 w-max min-w-full items-stretch gap-2 sm:gap-3 md:grid md:w-full md:min-w-0 md:gap-2 lg:gap-3'
                }
                style={
                  !embedded && displayLists.length > 0
                    ? {
                        gridTemplateColumns: `repeat(${displayLists.length}, minmax(0, 1fr))`,
                      }
                    : undefined
                }
              >
                {displayLists.map((list) => (
                  <div
                    key={list.uuid}
                    className={
                      embedded
                        ? 'flex h-full min-h-0 w-[260px] shrink-0 flex-col rounded-lg border border-black/10 bg-black/2 sm:w-[280px]'
                        : 'flex h-full min-h-0 w-[min(100%,14rem)] shrink-0 flex-col rounded-lg border border-black/10 bg-black/2 sm:w-64 md:min-w-0 md:max-w-none md:w-auto'
                    }
                    onDragOver={onDragOver}
                    onDrop={(e) => onDropOnColumn(e, list)}
                  >
                    <div className="shrink-0 border-b border-black/10 bg-white px-2.5 py-2 text-sm font-semibold text-ink">
                      {list.title}
                    </div>
                    <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2">
                      {sortedCards(list).map((card, index) => {
                        const createdPhaseLabel = labelForCreatedPhase(card.created_in_phase)
                        return (
                          <div
                            key={card.uuid}
                            draggable
                            onDragStart={(e) => onDragStartCard(e, card.uuid)}
                            onDragEnd={onDragEnd}
                            onDragOver={onDragOver}
                            onDrop={(e) => onDropOnCard(e, list, index)}
                            className="flex gap-2 rounded-md border border-black/10 bg-white px-2 py-2 text-left text-sm shadow-card transition hover:border-primary/30"
                          >
                            <div
                              className="mt-0.5 shrink-0 cursor-grab text-black/35 active:cursor-grabbing"
                              aria-hidden
                              title="Arrastrar para mover"
                            >
                              <svg width="16" height="20" viewBox="0 0 16 20" className="block">
                                <circle cx="5" cy="5" r="1.5" fill="currentColor" />
                                <circle cx="11" cy="5" r="1.5" fill="currentColor" />
                                <circle cx="5" cy="10" r="1.5" fill="currentColor" />
                                <circle cx="11" cy="10" r="1.5" fill="currentColor" />
                                <circle cx="5" cy="15" r="1.5" fill="currentColor" />
                                <circle cx="11" cy="15" r="1.5" fill="currentColor" />
                              </svg>
                            </div>
                            <button
                              type="button"
                              className="min-w-0 flex-1 cursor-pointer text-left"
                              onClick={() => openCard(card)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                  e.preventDefault()
                                  openCard(card)
                                }
                              }}
                            >
                              <div className="font-medium text-ink">{card.title}</div>
                              {card.description ? (
                                <p className="mt-1 line-clamp-2 text-xs text-muted">{card.description}</p>
                              ) : null}
                              <div className="mt-2 space-y-1.5 border-t border-black/8 pt-2 text-[11px]">
                                {createdPhaseLabel ? (
                                  <div className="flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-2">
                                    <span className="shrink-0 font-semibold uppercase tracking-wide text-muted">
                                      Creada en fase
                                    </span>
                                    <span className="text-ink">{createdPhaseLabel}</span>
                                  </div>
                                ) : null}
                                <div className="flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-2">
                                  <span className="shrink-0 font-semibold uppercase tracking-wide text-muted">
                                    Asignado
                                  </span>
                                  <span className="break-all text-ink">{card.assignee_email ?? '—'}</span>
                                </div>
                                <div className="flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-2">
                                  <span className="shrink-0 font-semibold uppercase tracking-wide text-muted">
                                    Por
                                  </span>
                                  <span className="break-all text-ink">{card.creator_email ?? '—'}</span>
                                </div>
                              </div>
                            </button>
                            <button
                              type="button"
                              className="shrink-0 self-start rounded-md border border-primary/50 bg-primary/[0.06] px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-primary hover:bg-primary/[0.12]"
                              onClick={(e) => {
                                e.stopPropagation()
                                openCard(card)
                              }}
                            >
                              View
                            </button>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {!embedded && includeArchived && displayArchivedCards.length > 0 ? (
            <div className="shrink-0 border-t border-black/10 pt-6">
              <h2 className="text-lg font-semibold text-ink">Archivadas</h2>
              <p className="du-meta mt-1">Clic para ver detalle o restaurar.</p>
              <div className="mt-4 flex max-h-[min(40vh,24rem)] flex-wrap gap-2 overflow-y-auto">
                {displayArchivedCards.map((c) => (
                  <button
                    key={c.uuid}
                    type="button"
                    className="max-w-xs rounded-md border border-black/10 bg-white px-3 py-2 text-left text-sm shadow-card hover:border-primary/30"
                    onClick={() => setModalCard(c)}
                  >
                    <div className="font-medium text-ink">{c.title}</div>
                    <div className="du-meta mt-1 line-clamp-1">{c.assignee_email ?? 'Sin asignar'}</div>
                  </button>
                ))}
              </div>
            </div>
          ) : null}
          {embedded && includeArchived && displayArchivedCards.length > 0 ? (
            <div className="shrink-0 border-t border-black/10 pt-2">
              <p className="text-xs font-medium text-ink">Archivadas ({displayArchivedCards.length})</p>
              <div className="mt-1 flex max-h-24 flex-wrap gap-1 overflow-y-auto">
                {displayArchivedCards.map((c) => (
                  <button
                    key={c.uuid}
                    type="button"
                    className="max-w-[10rem] truncate rounded border border-black/10 bg-white px-2 py-1 text-left text-xs hover:border-primary/30"
                    onClick={() => setModalCard(c)}
                  >
                    {c.title}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </>
      )}

      {modalCard && token ? (
        <TaskboardCardModal
          token={token}
          card={modalCard}
          assignees={assignees}
          readOnly={false}
          onClose={() => setModalCard(null)}
          onSaved={() => void load()}
        />
      ) : null}

      {createOpen && token && listOptions.length > 0 ? (
        <TaskboardCreateModal
          token={token}
          lists={listOptions}
          assignees={assignees}
          defaultProjectUuid={projectFilter || undefined}
          onClose={() => setCreateOpen(false)}
          onCreated={() => void load()}
        />
      ) : null}
    </div>
  )
}
