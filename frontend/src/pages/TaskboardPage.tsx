import { useCallback, useEffect, useState } from 'react'

import { apiFetch } from '../api/client'
import { PrimaryButton } from '../components/PrimaryButton'
import { useAuthStore } from '../store/authStore'

const CARD_MIME = 'application/x-dupla-task-card'

type TaskCard = {
  uuid: string
  title: string
  description: string | null
  position: number
  list_uuid: string
  created_at: string
  created_by_uuid: string | null
}

type TaskList = {
  uuid: string
  title: string
  position: number
  cards: TaskCard[]
}

type Board = { lists: TaskList[] }

export function TaskboardPage() {
  const token = useAuthStore((s) => s.token)
  const role = useAuthStore((s) => s.role)
  const readOnly = role === 'MASTER'
  const [board, setBoard] = useState<Board | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [newTitle, setNewTitle] = useState<Record<string, string>>({})
  const [creating, setCreating] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!token) return
    setError(null)
    const res = await apiFetch('/api/tasks/board', { token })
    if (!res.ok) {
      setError('No se pudo cargar el tablero')
      setBoard(null)
      return
    }
    setBoard((await res.json()) as Board)
  }, [token])

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

  async function addCard(listUuid: string) {
    if (!token || readOnly) return
    const title = (newTitle[listUuid] ?? '').trim()
    if (!title) return
    setCreating(listUuid)
    try {
      const res = await apiFetch('/api/tasks/cards', {
        method: 'POST',
        token,
        body: JSON.stringify({ list_uuid: listUuid, title }),
      })
      if (!res.ok) return
      setNewTitle((prev) => ({ ...prev, [listUuid]: '' }))
      await load()
    } finally {
      setCreating(null)
    }
  }

  function onDragStart(e: React.DragEvent, cardUuid: string) {
    if (readOnly) {
      e.preventDefault()
      return
    }
    e.dataTransfer.setData(CARD_MIME, cardUuid)
    e.dataTransfer.effectAllowed = 'move'
  }

  function onDragOver(e: React.DragEvent) {
    if (readOnly) return
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  function sortedCards(list: TaskList): TaskCard[] {
    return [...list.cards].sort((a, b) => a.position - b.position || a.uuid.localeCompare(b.uuid))
  }

  function onDropOnColumn(e: React.DragEvent, list: TaskList) {
    e.preventDefault()
    if (readOnly) return
    const cardUuid = e.dataTransfer.getData(CARD_MIME)
    if (!cardUuid) return
    const without = sortedCards(list).filter((c) => c.uuid !== cardUuid)
    void moveCard(cardUuid, list.uuid, without.length)
  }

  function onDropOnCard(e: React.DragEvent, list: TaskList, insertIndex: number) {
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

  if (loading) {
    return <p className="text-sm text-muted">Cargando tablero…</p>
  }

  if (error || !board) {
    return <p className="text-sm text-primary">{error ?? 'Sin datos'}</p>
  }

  const lists = [...board.lists].sort((a, b) => a.position - b.position)

  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-ink">Tablero de tareas</h1>
        <p className="mt-2 text-sm text-muted">
          {readOnly
            ? 'Como administrador (MASTER) puedes ver el tablero. Coordinadores y operarios mueven y crean tarjetas.'
            : 'Arrastra tarjetas entre columnas o reordena dentro de la misma lista.'}
        </p>
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
            <div className="flex flex-1 flex-col gap-2 p-2">
              {sortedCards(list).map((card, index) => (
                  <div
                    key={card.uuid}
                    draggable={!readOnly}
                    onDragStart={(e) => onDragStart(e, card.uuid)}
                    onDragOver={onDragOver}
                    onDrop={(e) => onDropOnCard(e, list, index)}
                    className={`rounded-md border border-black/10 bg-white px-3 py-2 text-sm shadow-card ${
                      readOnly ? '' : 'cursor-grab active:cursor-grabbing'
                    }`}
                  >
                    <div className="font-medium text-ink">{card.title}</div>
                    {card.description ? (
                      <p className="mt-1 text-xs text-muted">{card.description}</p>
                    ) : null}
                  </div>
                ))}
              {!readOnly ? (
                <div className="mt-1 space-y-2 border-t border-black/5 pt-2">
                  <input
                    className="du-input text-sm"
                    placeholder="Nueva tarjeta…"
                    value={newTitle[list.uuid] ?? ''}
                    onChange={(e) =>
                      setNewTitle((prev) => ({ ...prev, [list.uuid]: e.target.value }))
                    }
                    aria-label={`Nueva tarjeta en ${list.title}`}
                  />
                  <PrimaryButton
                    type="button"
                    className="w-full text-sm"
                    disabled={creating === list.uuid || !(newTitle[list.uuid] ?? '').trim()}
                    onClick={() => void addCard(list.uuid)}
                  >
                    {creating === list.uuid ? 'Añadiendo…' : 'Añadir'}
                  </PrimaryButton>
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
