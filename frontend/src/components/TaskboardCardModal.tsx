import { useEffect, useState } from 'react'

import { apiFetch } from '../api/client'
import { PrimaryButton } from './PrimaryButton'
import type { TaskAssigneeOption, TaskCardDto } from '../types/taskBoard'

type Props = {
  token: string
  card: TaskCardDto
  assignees: TaskAssigneeOption[]
  readOnly: boolean
  onClose: () => void
  onSaved: () => void
}

export function TaskboardCardModal({ token, card, assignees, readOnly, onClose, onSaved }: Props) {
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(card.title)
  const [description, setDescription] = useState(card.description ?? '')
  const [assigneeUuid, setAssigneeUuid] = useState<string>(card.assignee_uuid ?? '')
  const [archived, setArchived] = useState(card.archived)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setEditing(false)
    setTitle(card.title)
    setDescription(card.description ?? '')
    setAssigneeUuid(card.assignee_uuid ?? '')
    setArchived(card.archived)
    setError(null)
  }, [card])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function save() {
    if (readOnly) return
    setError(null)
    setSaving(true)
    try {
      const body: Record<string, unknown> = {
        title: title.trim(),
        description: description.trim() || null,
        assignee_uuid: assigneeUuid || null,
        archived,
      }
      const res = await apiFetch(`/api/tasks/cards/${card.uuid}`, {
        method: 'PATCH',
        token,
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        setError((j as { detail?: string }).detail ?? 'No se pudo guardar')
        return
      }
      onSaved()
      setEditing(false)
      onClose()
    } finally {
      setSaving(false)
    }
  }

  function cancelEdit() {
    setTitle(card.title)
    setDescription(card.description ?? '')
    setAssigneeUuid(card.assignee_uuid ?? '')
    setArchived(card.archived)
    setError(null)
    setEditing(false)
  }

  const assigneeLabel =
    card.assignee_email ?? assignees.find((a) => a.uuid === card.assignee_uuid)?.email ?? 'Sin asignar'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-black/10 bg-white p-6 shadow-lg"
        role="dialog"
        aria-labelledby="task-modal-title"
        aria-modal="true"
      >
        <h2 id="task-modal-title" className="sr-only">
          Tarea
        </h2>
        {readOnly ? (
          <p className="du-meta">Solo lectura (administrador).</p>
        ) : null}

        <div className="mt-4 space-y-4">
          {!editing ? (
            <>
              <div>
                <h3 className="text-lg font-semibold leading-snug text-ink">{card.title}</h3>
              </div>
              <div>
                <div className="du-label">Descripción</div>
                {card.description?.trim() ? (
                  <p className="mt-1 whitespace-pre-wrap text-sm text-ink">{card.description}</p>
                ) : (
                  <p className="mt-1 text-sm text-muted">Sin descripción.</p>
                )}
              </div>
              <div>
                <div className="du-label">Asignado a</div>
                <p className="mt-1 text-sm text-ink">{assigneeLabel}</p>
              </div>
              <div className="rounded-md border border-black/10 bg-black/2 px-3 py-2 text-sm">
                <div className="du-meta">Creada por</div>
                <div className="text-ink">{card.creator_email ?? '—'}</div>
                <div className="du-meta mt-2">Creada</div>
                <div className="text-muted">
                  {new Date(card.created_at).toLocaleString(undefined, {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                </div>
              </div>
              {card.archived ? (
                <p className="text-sm text-muted">Archivada (no aparece en el tablero activo).</p>
              ) : null}
            </>
          ) : (
            <>
              <div>
                <label className="du-label" htmlFor="tm-title">
                  Título
                </label>
                <input
                  id="tm-title"
                  className="du-input mt-1"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  disabled={readOnly}
                  maxLength={255}
                />
              </div>
              <div>
                <label className="du-label" htmlFor="tm-desc">
                  Descripción breve
                </label>
                <textarea
                  id="tm-desc"
                  className="du-input mt-1 min-h-[72px] resize-y text-sm"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={readOnly}
                  maxLength={500}
                  rows={3}
                />
                <p className="du-meta mt-0.5">{description.length}/500</p>
              </div>
              <div>
                <label className="du-label" htmlFor="tm-assignee">
                  Asignado a
                </label>
                <select
                  id="tm-assignee"
                  className="du-input mt-1"
                  value={assigneeUuid}
                  onChange={(e) => setAssigneeUuid(e.target.value)}
                  disabled={readOnly}
                >
                  <option value="">Sin asignar</option>
                  {assignees.map((a) => (
                    <option key={a.uuid} value={a.uuid}>
                      {a.email}
                    </option>
                  ))}
                </select>
              </div>
              <div className="rounded-md border border-black/10 bg-black/2 px-3 py-2 text-sm">
                <div className="du-meta">Creada por</div>
                <div className="text-ink">{card.creator_email ?? '—'}</div>
                <div className="du-meta mt-2">Creada</div>
                <div className="text-muted">
                  {new Date(card.created_at).toLocaleString(undefined, {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                </div>
              </div>
              {!readOnly ? (
                <label className="flex items-center gap-2 text-sm text-ink">
                  <input
                    type="checkbox"
                    className="rounded border-black/20"
                    checked={archived}
                    onChange={(e) => setArchived(e.target.checked)}
                  />
                  Archivada (sale del tablero activo)
                </label>
              ) : card.archived ? (
                <p className="text-sm text-muted">Esta tarea está archivada.</p>
              ) : null}
            </>
          )}
          {error ? <p className="text-sm text-primary">{error}</p> : null}
        </div>

        <div className="mt-6 flex flex-wrap justify-end gap-2">
          {!editing ? (
            <>
              <button
                type="button"
                className="rounded-md px-3 py-2 text-sm text-muted hover:text-ink"
                onClick={onClose}
              >
                Cerrar
              </button>
              {!readOnly ? (
                <PrimaryButton type="button" onClick={() => setEditing(true)}>
                  Editar
                </PrimaryButton>
              ) : null}
            </>
          ) : (
            <>
              <button
                type="button"
                className="rounded-md px-3 py-2 text-sm text-muted hover:text-ink"
                onClick={cancelEdit}
                disabled={saving}
              >
                Cancelar
              </button>
              {!readOnly ? (
                <PrimaryButton type="button" disabled={saving || !title.trim()} onClick={() => void save()}>
                  {saving ? 'Guardando…' : 'Guardar'}
                </PrimaryButton>
              ) : null}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
