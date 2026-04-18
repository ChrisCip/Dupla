import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { boardQueryParams, cardMatchesSearch, CARD_MIME, labelForCreatedPhase } from '../lib/taskboard'
import { PrimaryButton } from './PrimaryButton'
import { TaskboardCardModal } from './TaskboardCardModal'
import { TaskboardCreateModal } from './TaskboardCreateModal'
import { TaskboardToolbar } from './TaskboardToolbar'
import { useAuthStore } from '../store/authStore'
import type { TaskAssigneeOption, TaskBoardDto, TaskCardDto, TaskListDto } from '../types/taskBoard'

export type TaskboardViewProps = {
  /** Filtro fijo por proyecto; vacío = tablero global */
  projectUuid?: string
  variant: 'full' | 'embedded'
  /**
   * En modo embebido: ancho máximo del viewport del tablero en columnas (resto con scroll horizontal).
   * Ej. 4 = se ven como mucho 4 columnas a la vez.
   */
  maxVisibleColumns?: number
  /** Oculta la franja de título «Tareas del proyecto» en embebido (el padre ya muestra el encabezado). */
  hideEmbeddedHeader?: boolean
}

export function TaskboardView({
  projectUuid: projectFilter = '',
  variant,
  maxVisibleColumns,
  hideEmbeddedHeader = false,
}: TaskboardViewProps) {
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

  const boardViewportMaxWidth = useMemo(() => {
    if (!embedded || maxVisibleColumns == null || maxVisibleColumns < 1) return undefined
    const colRem = 17.5
    const gapRem = 0.75
    const gaps = Math.max(0, maxVisibleColumns - 1)
    return `calc(${maxVisibleColumns} * ${colRem}rem + ${gaps} * ${gapRem}rem)`
  }, [embedded, maxVisibleColumns])

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
      ) : hideEmbeddedHeader ? (
        board ? (
          <div className="flex shrink-0 justify-end">
            <PrimaryButton type="button" className="shrink-0 py-1.5 text-sm" onClick={() => setCreateOpen(true)}>
              Añadir tarea
            </PrimaryButton>
          </div>
        ) : null
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
          <TaskboardToolbar
            embedded={embedded}
            boardSearch={boardSearch}
            setBoardSearch={setBoardSearch}
            mineOnly={mineOnly}
            setMineOnly={setMineOnly}
            filterAssignee={filterAssignee}
            setFilterAssignee={setFilterAssignee}
            includeArchived={includeArchived}
            setIncludeArchived={setIncludeArchived}
            assignees={assignees}
            todosSelected={todosSelected}
          />

          <div
            className={`flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-black/10 bg-black/2 shadow-[var(--shadow-card)] ${embedded ? 'min-h-0' : ''}`}
          >
            <div
              className={
                embedded
                  ? 'mx-auto min-h-0 w-full flex-1 overflow-x-auto overflow-y-hidden p-2'
                  : 'min-h-0 flex-1 overflow-x-auto overflow-y-hidden p-2'
              }
              style={boardViewportMaxWidth ? { maxWidth: boardViewportMaxWidth } : undefined}
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
                        gridTemplateColumns: `repeat(${displayLists.length}, minmax(17.5rem, 1fr))`,
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
                        : 'flex h-full min-h-0 w-[min(100%,17.5rem)] shrink-0 flex-col rounded-lg border border-black/10 bg-black/2 sm:w-72 md:min-w-0 md:max-w-none md:w-auto md:min-w-[17.5rem]'
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
                            className="flex min-w-0 gap-2 rounded-md border border-black/10 bg-white px-2 py-2 text-left text-sm shadow-card transition hover:border-primary/30"
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
                              <div className="mt-2 space-y-2 border-t border-black/8 pt-2 text-[11px]">
                                {createdPhaseLabel ? (
                                  <div className="flex flex-col gap-0.5">
                                    <span className="font-semibold uppercase tracking-wide text-muted">
                                      Creada en fase
                                    </span>
                                    <span className="min-w-0 break-words text-ink">{createdPhaseLabel}</span>
                                  </div>
                                ) : null}
                                <div className="flex flex-col gap-0.5">
                                  <span className="font-semibold uppercase tracking-wide text-muted">
                                    Asignado
                                  </span>
                                  <span className="min-w-0 break-words text-ink">{card.assignee_email ?? '—'}</span>
                                </div>
                                <div className="flex flex-col gap-0.5">
                                  <span className="font-semibold uppercase tracking-wide text-muted">Por</span>
                                  <span className="min-w-0 break-words text-ink">{card.creator_email ?? '—'}</span>
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
