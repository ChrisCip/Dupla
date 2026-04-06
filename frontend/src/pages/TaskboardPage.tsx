import { useCallback, useEffect, useRef, useState } from 'react'

import { apiFetch } from '../api/client'
import { PrimaryButton } from '../components/PrimaryButton'
import { TaskboardCardModal } from '../components/TaskboardCardModal'
import { TaskboardCreateModal } from '../components/TaskboardCreateModal'
import { useAuthStore } from '../store/authStore'
import type { TaskAssigneeOption, TaskBoardDto, TaskCardDto, TaskListDto } from '../types/taskBoard'

const CARD_MIME = 'application/x-dupla-task-card'

function boardQueryParams(mine: boolean, assigneeUuid: string, includeArchived: boolean): string {
  const p = new URLSearchParams()
  if (includeArchived) p.set('include_archived', 'true')
  if (mine) p.set('mine', 'true')
  else if (assigneeUuid) p.set('assignee_uuid', assigneeUuid)
  const s = p.toString()
  return s ? `?${s}` : ''
}

export function TaskboardPage() {
  const token = useAuthStore((s) => s.token)
  const role = useAuthStore((s) => s.role)
  const readOnly = role === 'MASTER'
  const [board, setBoard] = useState<TaskBoardDto | null>(null)
  const [assignees, setAssignees] = useState<TaskAssigneeOption[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [includeArchived, setIncludeArchived] = useState(false)
  const [mineOnly, setMineOnly] = useState(false)
  const [filterAssignee, setFilterAssignee] = useState('')
  const [modalCard, setModalCard] = useState<TaskCardDto | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const dragRef = useRef(false)

  const load = useCallback(async () => {
    if (!token) return
    setError(null)
    const qs = boardQueryParams(mineOnly, filterAssignee, includeArchived)
    const res = await apiFetch(`/api/tasks/board${qs}`, { token })
    if (!res.ok) {
      setError('No se pudo cargar el tablero')
      setBoard(null)
      return
    }
    setBoard((await res.json()) as TaskBoardDto)
  }, [token, mineOnly, filterAssignee, includeArchived])

  const loadAssignees = useCallback(async () => {
    if (!token) return
    const res = await apiFetch('/api/tasks/assignees', { token })
    if (!res.ok) return
    setAssignees((await res.json()) as TaskAssigneeOption[])
  }, [token])

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
    if (!token || readOnly) return
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
    if (readOnly) {
      e.preventDefault()
      return
    }
    dragRef.current = true
    e.dataTransfer.setData(CARD_MIME, cardUuid)
    e.dataTransfer.effectAllowed = 'move'
  }

  function onDragOver(e: React.DragEvent) {
    if (readOnly) return
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  function sortedCards(list: TaskListDto): TaskCardDto[] {
    return [...list.cards].sort((a, b) => a.position - b.position || a.uuid.localeCompare(b.uuid))
  }

  function onDropOnColumn(e: React.DragEvent, list: TaskListDto) {
    e.preventDefault()
    if (readOnly) return
    const cardUuid = e.dataTransfer.getData(CARD_MIME)
    if (!cardUuid) return
    const without = sortedCards(list).filter((c) => c.uuid !== cardUuid)
    void moveCard(cardUuid, list.uuid, without.length)
  }

  function onDropOnCard(e: React.DragEvent, list: TaskListDto, insertIndex: number) {
    e.preventDefault()
    e.stopPropagation()
    if (readOnly) return
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

  if (loading) {
    return <p className="text-sm text-muted">Cargando tablero…</p>
  }

  if (error || !board) {
    return <p className="text-sm text-primary">{error ?? 'Sin datos'}</p>
  }

  const lists = [...board.lists].sort((a, b) => a.position - b.position)
  const listOptions = lists.map((l) => ({ uuid: l.uuid, title: l.title }))

  return (
    <>
      <div className="mb-6 space-y-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-ink">Tablero de tareas</h1>
            <p className="mt-2 text-sm text-muted">
              {readOnly
                ? 'Como administrador (MASTER) puedes ver el tablero. Coordinadores y operarios editan, asignan y archivan.'
                : 'Asigna personas, descripciones breves y archiva lo completado. Clic en una tarjeta para el detalle.'}
            </p>
          </div>
          {!readOnly ? (
            <PrimaryButton type="button" className="shrink-0 self-start" onClick={() => setCreateOpen(true)}>
              Añadir tarea
            </PrimaryButton>
          ) : null}
        </div>
        <div className="flex flex-wrap items-end gap-4 rounded-lg border border-black/10 bg-white p-4">
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              className="rounded border-black/20"
              checked={mineOnly}
              onChange={(e) => {
                setMineOnly(e.target.checked)
                if (e.target.checked) setFilterAssignee('')
              }}
            />
            Solo mis tareas
          </label>
          <div className="min-w-[200px]">
            <span className="du-label">Asignado</span>
            <select
              className="du-input mt-1 text-sm"
              value={filterAssignee}
              disabled={mineOnly}
              onChange={(e) => setFilterAssignee(e.target.value)}
              aria-label="Filtrar por asignado"
            >
              <option value="">Todos</option>
              {assignees.map((a) => (
                <option key={a.uuid} value={a.uuid}>
                  {a.email}
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              className="rounded border-black/20"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
            />
            Mostrar archivadas abajo
          </label>
        </div>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4">
        {lists.map((list) => (
          <div
            key={list.uuid}
            className="flex w-72 shrink-0 flex-col rounded-lg border border-black/10 bg-black/2"
            onDragOver={onDragOver}
            onDrop={(e) => onDropOnColumn(e, list)}
          >
            <div className="border-b border-black/10 px-3 py-2 text-sm font-semibold text-ink">
              {list.title}
            </div>
            <div className="flex min-h-[120px] flex-1 flex-col gap-2 p-2">
              {sortedCards(list).map((card, index) => (
                <div
                  key={card.uuid}
                  draggable={!readOnly}
                  onDragStart={(e) => onDragStartCard(e, card.uuid)}
                  onDragEnd={onDragEnd}
                  onDragOver={onDragOver}
                  onDrop={(e) => onDropOnCard(e, list, index)}
                  onClick={() => openCard(card)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      openCard(card)
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  className={`rounded-md border border-black/10 bg-white px-3 py-2 text-left text-sm shadow-card transition hover:border-primary/30 ${
                    readOnly ? '' : 'cursor-grab active:cursor-grabbing'
                  }`}
                >
                  <div className="font-medium text-ink">{card.title}</div>
                  {card.description ? (
                    <p className="mt-1 line-clamp-2 text-xs text-muted">{card.description}</p>
                  ) : null}
                  <div className="mt-2 space-y-0.5 border-t border-black/5 pt-2 text-[11px] text-muted">
                    <div>
                      <span className="text-ink/70">Asignado:</span>{' '}
                      {card.assignee_email ?? '—'}
                    </div>
                    <div>
                      <span className="text-ink/70">Por:</span> {card.creator_email ?? '—'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {includeArchived && board.archived_cards.length > 0 ? (
        <div className="mt-10 border-t border-black/10 pt-8">
          <h2 className="text-lg font-semibold text-ink">Archivadas</h2>
          <p className="du-meta mt-1">Clic para ver detalle o restaurar.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {board.archived_cards.map((c) => (
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

      {modalCard && token ? (
        <TaskboardCardModal
          token={token}
          card={modalCard}
          assignees={assignees}
          readOnly={readOnly}
          onClose={() => setModalCard(null)}
          onSaved={() => void load()}
        />
      ) : null}

      {createOpen && token && listOptions.length > 0 ? (
        <TaskboardCreateModal
          token={token}
          lists={listOptions}
          assignees={assignees}
          onClose={() => setCreateOpen(false)}
          onCreated={() => void load()}
        />
      ) : null}
    </>
  )
}
