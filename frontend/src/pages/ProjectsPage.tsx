import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { Card } from '../components/Card'
import { PrimaryButton } from '../components/PrimaryButton'
import {
  NEXT_WORKFLOW_PHASE,
  PREV_WORKFLOW_PHASE,
  WORKFLOW_PHASE_LABELS,
  WORKFLOW_PHASE_ORDER,
} from '../constants/workflowPhases'
import type { Project } from '../types/project'
import { useAuthStore } from '../store/authStore'

const PROJECT_CARD_MIME = 'application/x-dupla-project'

function formatProjectUpdatedAt(iso: string | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('es', { dateStyle: 'short', timeStyle: 'short' })
}

export function ProjectsPage() {
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.token)
  const role = useAuthStore((s) => s.role)
  const userUuid = useAuthStore((s) => s.userUuid)
  const [projects, setProjects] = useState<Project[]>([])
  const [name, setName] = useState('Nuevo proyecto')
  const [client, setClient] = useState('')
  const [createMembers, setCreateMembers] = useState<Set<string>>(new Set())
  const [adminUsersCreate, setAdminUsersCreate] = useState<{ uuid: string; email: string }[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loadingList, setLoadingList] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)
  const feedbackClearRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [viewMode, setViewMode] = useState<'lista' | 'tablero'>('tablero')
  const [boardMsg, setBoardMsg] = useState<string | null>(null)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const dragRef = useRef(false)

  const refresh = useCallback(async () => {
    if (!token) return
    setError(null)
    const res = await apiFetch('/api/projects', { token })
    if (!res.ok) {
      setError('No se pudieron cargar proyectos')
      return
    }
    setProjects((await res.json()) as Project[])
  }, [token])

  useEffect(() => {
    let cancelled = false
    async function run() {
      setLoadingList(true)
      await refresh()
      if (!cancelled) setLoadingList(false)
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [refresh])

  useEffect(() => {
    if (role !== 'GERENCIA' || !token) return
    let cancelled = false
    void (async () => {
      const u = await apiFetch('/api/admin/users', { token })
      if (cancelled || !u.ok) return
      setAdminUsersCreate((await u.json()) as { uuid: string; email: string }[])
    })()
    return () => {
      cancelled = true
    }
  }, [role, token])

  useEffect(() => {
    return () => {
      if (feedbackClearRef.current) clearTimeout(feedbackClearRef.current)
    }
  }, [])

  useEffect(() => {
    if (!createModalOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setCreateModalOpen(false)
        setError(null)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [createModalOpen])

  function closeCreateModal() {
    setCreateModalOpen(false)
    setError(null)
  }

  async function createProject(e: React.FormEvent) {
    e.preventDefault()
    if (!token) return
    setError(null)
    setSubmitting(true)
    try {
      const body: Record<string, unknown> = { name, client_name: client || null }
      if (role === 'GERENCIA') {
        body.member_user_uuids = Array.from(createMembers)
      }
      const res = await apiFetch('/api/projects', {
        method: 'POST',
        token,
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        setError('No se pudo crear el proyecto')
        return
      }
      setFeedback('Proyecto creado. Ábrelo en la tabla o en el tablero, o crea otro.')
      if (feedbackClearRef.current) clearTimeout(feedbackClearRef.current)
      feedbackClearRef.current = setTimeout(() => setFeedback(null), 6000)
      setName('Nuevo proyecto')
      setClient('')
      setCreateMembers(new Set())
      closeCreateModal()
      await refresh()
    } finally {
      setSubmitting(false)
    }
  }

  async function transitionProjectOnBoard(p: Project, targetPhase: string) {
    if (!token) return
    const next = NEXT_WORKFLOW_PHASE[p.workflow_phase]
    const prev = PREV_WORKFLOW_PHASE[p.workflow_phase]
    if (next !== targetPhase && prev !== targetPhase) {
      setBoardMsg('Solo puedes mover el proyecto a la fase inmediatamente anterior o siguiente.')
      return
    }
    setBoardMsg(null)
    const res = await apiFetch(`/api/projects/${p.uuid}/transitions`, {
      method: 'POST',
      token,
      body: JSON.stringify({ target_phase: targetPhase }),
    })
    const j = await res.json().catch(() => ({}))
    if (!res.ok) {
      setBoardMsg((j as { detail?: string }).detail ?? 'No se pudo actualizar la fase')
      return
    }
    await refresh()
  }

  function onDragEndBoard() {
    window.setTimeout(() => {
      dragRef.current = false
    }, 0)
  }

  function onDragStartProject(e: React.DragEvent, projectUuid: string) {
    dragRef.current = true
    e.dataTransfer.setData(PROJECT_CARD_MIME, projectUuid)
    e.dataTransfer.effectAllowed = 'move'
  }

  function onDragOverBoard(e: React.DragEvent) {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  function onDropOnPhaseColumn(e: React.DragEvent, phaseKey: string) {
    e.preventDefault()
    const id = e.dataTransfer.getData(PROJECT_CARD_MIME)
    if (!id) return
    const p = projects.find((x) => x.uuid === id)
    if (!p) return
    void transitionProjectOnBoard(p, phaseKey)
  }

  function openCard(projectUuid: string) {
    if (dragRef.current) return
    navigate(`/app/projects/${projectUuid}`)
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-6">
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {feedback ?? ''}
      </div>
      {feedback ? (
        <div
          className="du-callout flex flex-wrap items-center justify-between gap-3 border-primary/25"
          role="status"
        >
          <span>{feedback}</span>
          <button
            type="button"
            className="du-link text-xs uppercase tracking-wide"
            onClick={() => setFeedback(null)}
          >
            Cerrar
          </button>
        </div>
      ) : null}
      <div className="flex shrink-0 flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold text-ink">Proyectos</h1>
          <p className="mt-1 text-sm text-muted">
            {role === 'GERENCIA'
              ? 'Tablero por fase o lista. Arrastra una tarjeta a la columna de al lado para ir a la fase anterior o siguiente (Gerencia o Control pueden retroceder).'
              : 'Proyectos a los que tienes acceso.'}
          </p>
        </div>
        <div className="flex shrink-0 gap-2 rounded-lg border border-black/10 bg-white p-1 text-sm shadow-[var(--shadow-card)]">
          <button
            type="button"
            className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
              viewMode === 'tablero' ? 'bg-primary/12 text-ink ring-1 ring-primary/25' : 'text-muted hover:text-ink'
            }`}
            onClick={() => setViewMode('tablero')}
          >
            Tablero por fase
          </button>
          <button
            type="button"
            className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
              viewMode === 'lista' ? 'bg-primary/12 text-ink ring-1 ring-primary/25' : 'text-muted hover:text-ink'
            }`}
            onClick={() => setViewMode('lista')}
          >
            Lista
          </button>
        </div>
      </div>

      {viewMode === 'lista' ? (
        <Card className="mx-auto flex min-h-0 w-full max-w-4xl flex-1 flex-col overflow-hidden p-0">
          {role === 'GERENCIA' ? (
            <div className="flex shrink-0 items-center justify-end border-b border-black/10 bg-white px-3 py-2">
              <PrimaryButton type="button" className="px-3 py-1.5 text-sm" onClick={() => setCreateModalOpen(true)}>
                Nuevo proyecto
              </PrimaryButton>
            </div>
          ) : null}
          <div className="min-h-0 flex-1 overflow-auto">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 z-10 bg-black/4 text-[10px] uppercase tracking-wide text-muted backdrop-blur-sm">
                <tr>
                  <th className="px-2 py-2">Nombre</th>
                  <th className="px-2 py-2">Cliente</th>
                  <th className="hidden px-2 py-2 sm:table-cell">Fase</th>
                  <th className="whitespace-nowrap px-2 py-2">Modif.</th>
                  <th className="px-2 py-2" />
                </tr>
              </thead>
              <tbody>
                {loadingList ? (
                  <tr>
                    <td
                      className="border-l-4 border-l-primary bg-primary/[0.04] px-3 py-3 text-muted"
                      colSpan={5}
                    >
                      Cargando lista de proyectos…
                    </td>
                  </tr>
                ) : null}
                {!loadingList &&
                  projects.map((p) => (
                    <tr
                      key={p.uuid}
                      tabIndex={0}
                      className="cursor-pointer border-t border-black/5 transition-colors duration-150 hover:bg-black/[0.04] focus-visible:bg-black/[0.04] focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-primary/40"
                      onClick={() => navigate(`/app/projects/${p.uuid}`)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          navigate(`/app/projects/${p.uuid}`)
                        }
                      }}
                    >
                      <td className="max-w-[10rem] truncate px-2 py-1.5 font-medium text-ink sm:max-w-none">
                        {p.name}
                      </td>
                      <td className="max-w-[7rem] truncate px-2 py-1.5 text-muted sm:max-w-[9rem]">
                        {p.client_name ?? '—'}
                      </td>
                      <td className="hidden px-2 py-1.5 text-muted sm:table-cell">
                        <span className="inline-block max-w-[11rem] truncate rounded bg-black/[0.06] px-1.5 py-0.5 text-[10px] font-medium text-ink">
                          {WORKFLOW_PHASE_LABELS[p.workflow_phase] ?? p.workflow_phase}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-2 py-1.5 text-[11px] tabular-nums text-muted">
                        {formatProjectUpdatedAt(p.updated_at)}
                      </td>
                      <td className="px-2 py-1.5 text-right">
                        <Link
                          className="du-link text-[11px]"
                          to={`/app/projects/${p.uuid}`}
                          onClick={(e) => e.stopPropagation()}
                        >
                          Abrir →
                        </Link>
                      </td>
                    </tr>
                  ))}
                {!loadingList && projects.length === 0 ? (
                  <tr>
                    <td className="px-4 py-10" colSpan={5}>
                      <div className="mx-auto max-w-md rounded-lg border border-dashed border-black/15 bg-black/[0.02] px-6 py-8 text-center">
                        <p className="text-sm font-medium text-ink">Todavía no hay proyectos</p>
                        <p className="mt-2 text-sm text-muted">
                          {role === 'GERENCIA'
                            ? 'Usa «Nuevo proyecto» para crear el primero. También puedes verlos en el tablero por fase.'
                            : 'Cuando un administrador te dé acceso, el proyecto aparecerá aquí.'}
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <Card className="flex min-h-0 flex-1 flex-col overflow-hidden p-0">
          {role === 'GERENCIA' || boardMsg ? (
            <div
              className={`flex shrink-0 flex-wrap items-center gap-3 border-b border-black/10 bg-white px-4 py-3 ${
                boardMsg && role === 'GERENCIA'
                  ? 'justify-between'
                  : boardMsg
                    ? 'justify-start'
                    : 'justify-end'
              }`}
            >
              {boardMsg ? (
                <p className={`text-sm text-primary ${role === 'GERENCIA' ? 'min-w-0 flex-1' : ''}`}>{boardMsg}</p>
              ) : null}
              {role === 'GERENCIA' ? (
                <PrimaryButton
                  type="button"
                  className="shrink-0"
                  onClick={() => setCreateModalOpen(true)}
                >
                  Nuevo proyecto
                </PrimaryButton>
              ) : null}
            </div>
          ) : null}
          {loadingList ? (
            <p className="shrink-0 px-4 py-6 text-sm text-muted">Cargando tablero…</p>
          ) : (
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden p-1.5 pb-2">
              <div className="min-h-0 flex-1 overflow-x-auto overflow-y-hidden">
                <div className="flex h-full w-max min-w-full items-stretch gap-1.5">
              {WORKFLOW_PHASE_ORDER.map((phaseKey) => {
                const label = WORKFLOW_PHASE_LABELS[phaseKey] ?? phaseKey
                const inColumn = projects.filter((p) => p.workflow_phase === phaseKey)
                return (
                  <div
                    key={phaseKey}
                    className="flex h-full min-h-0 w-[8.5rem] shrink-0 flex-col rounded-lg border border-black/10 bg-black/[0.02] shadow-[var(--shadow-card)] sm:w-[9rem]"
                    onDragOver={onDragOverBoard}
                    onDrop={(e) => onDropOnPhaseColumn(e, phaseKey)}
                  >
                    <div
                      className="shrink-0 border-b border-black/10 bg-white px-1 py-1 text-[8px] font-semibold uppercase leading-tight tracking-wide text-muted sm:text-[9px]"
                      title={label}
                    >
                      <span className="line-clamp-2">{label}</span>
                    </div>
                    <div className="min-h-0 flex-1 space-y-1 overflow-y-auto p-1">
                      {inColumn.map((p) => {
                        const hasNext = NEXT_WORKFLOW_PHASE[p.workflow_phase] !== undefined
                        const hasPrev = PREV_WORKFLOW_PHASE[p.workflow_phase] !== undefined
                        const canMovePhase = hasNext || hasPrev
                        return (
                          <div
                            key={p.uuid}
                            role="button"
                            tabIndex={0}
                            draggable={canMovePhase}
                            className={`group relative cursor-pointer overflow-hidden rounded-md border border-black/10 bg-white text-left shadow-sm ring-1 ring-black/[0.04] transition-all duration-200 hover:-translate-y-px hover:border-black/20 hover:shadow-md hover:ring-black/10 ${
                              canMovePhase ? '' : 'opacity-[0.92]'
                            }`}
                            onClick={() => openCard(p.uuid)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault()
                                openCard(p.uuid)
                              }
                            }}
                            onDragStart={(e) => onDragStartProject(e, p.uuid)}
                            onDragEnd={onDragEndBoard}
                          >
                            <div
                              className={`absolute inset-y-1 left-0 w-0.5 rounded-full ${canMovePhase ? 'bg-primary' : 'bg-black/20'}`}
                              aria-hidden
                            />
                            <div className="relative pl-2 pr-1.5 pb-1.5 pt-1">
                              <h3 className="line-clamp-2 pr-0.5 text-[10px] font-semibold leading-snug tracking-tight text-ink sm:text-[11px]">
                                {p.name}
                              </h3>
                              <div className="mt-1 space-y-0.5">
                                <div className="flex items-start gap-0.5">
                                  <span className="du-meta w-8 shrink-0 text-[8px]">Cliente</span>
                                  <span className="min-w-0 flex-1 text-[9px] leading-snug text-ink sm:text-[10px]">
                                    {p.client_name?.trim() ? (
                                      <span className="line-clamp-2">{p.client_name}</span>
                                    ) : (
                                      <span className="text-muted">—</span>
                                    )}
                                  </span>
                                </div>
                                <div className="flex items-start gap-0.5 border-t border-black/[0.06] pt-0.5">
                                  <span className="du-meta w-8 shrink-0 text-[8px]">Act.</span>
                                  <time
                                    className="min-w-0 flex-1 text-[8px] tabular-nums leading-snug text-ink sm:text-[9px]"
                                    dateTime={p.updated_at}
                                  >
                                    {formatProjectUpdatedAt(p.updated_at)}
                                  </time>
                                </div>
                              </div>
                              <div className="mt-1 flex items-start justify-between gap-0.5 border-t border-black/[0.05] pt-1">
                                {!canMovePhase ? (
                                  <span className="rounded bg-black/[0.05] px-0.5 py-0.5 text-[7px] font-semibold uppercase leading-tight tracking-wide text-muted">
                                    Fin flujo
                                  </span>
                                ) : (
                                  <span className="text-[7px] font-medium uppercase leading-tight tracking-wide text-muted sm:text-[8px]">
                                    {hasPrev ? '←' : ''}
                                    {hasPrev && hasNext ? ' ' : ''}
                                    {hasNext ? '→' : ''}
                                  </span>
                                )}
                                <span className="text-[8px] font-medium leading-tight text-muted opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                                  Abrir →
                                </span>
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
                </div>
              </div>
            </div>
          )}
        </Card>
      )}

      {createModalOpen && role === 'GERENCIA' ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) closeCreateModal()
          }}
        >
          <div
            className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-black/10 bg-white p-6 shadow-lg"
            role="dialog"
            aria-labelledby="create-project-title"
            aria-modal="true"
          >
            <h2 id="create-project-title" className="text-lg font-semibold text-ink">
              Nuevo proyecto
            </h2>
            <p className="mt-2 text-sm text-muted">
              El nombre puede ser el código interno o la obra; el cliente ayuda a filtrar después. Los participantes se
              pueden ajustar después en <strong className="text-ink">Configuración</strong> del workspace.
            </p>
            <form onSubmit={createProject} className="mt-4 space-y-4">
              <div>
                <label htmlFor="modal-project-name" className="du-label">
                  Nombre
                </label>
                <input
                  id="modal-project-name"
                  className="du-input mt-1"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  aria-label="Nombre del proyecto"
                  disabled={submitting}
                  required
                  autoFocus
                />
              </div>
              <div>
                <label htmlFor="modal-project-client" className="du-label">
                  Cliente <span className="font-normal text-muted">(opcional)</span>
                </label>
                <input
                  id="modal-project-client"
                  className="du-input mt-1"
                  placeholder="Ej. Constructora …"
                  value={client}
                  onChange={(e) => setClient(e.target.value)}
                  aria-label="Cliente"
                  disabled={submitting}
                />
              </div>
              <div>
                <div className="du-label">Participantes (opcional)</div>
                <p className="mt-1 text-xs text-muted">
                  El creador ({userUuid ? 'tú' : 'admin'}) tiene acceso siempre. Marca quién más entra al equipo.
                </p>
                <ul className="mt-2 max-h-40 space-y-2 overflow-y-auto rounded-md border border-black/10 p-2 text-sm">
                  {adminUsersCreate.map((u) => {
                    const isSelf = userUuid !== null && u.uuid === userUuid
                    const checked = isSelf || createMembers.has(u.uuid)
                    return (
                      <li key={u.uuid} className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          id={`cm-${u.uuid}`}
                          className="mt-0.5"
                          checked={checked}
                          disabled={isSelf || submitting}
                          onChange={() => {
                            if (isSelf) return
                            setCreateMembers((prev) => {
                              const next = new Set(prev)
                              if (next.has(u.uuid)) next.delete(u.uuid)
                              else next.add(u.uuid)
                              return next
                            })
                          }}
                        />
                        <label htmlFor={`cm-${u.uuid}`} className={isSelf ? 'text-muted' : 'text-ink'}>
                          {u.email}
                          {isSelf ? <span className="du-meta"> (creador)</span> : null}
                        </label>
                      </li>
                    )
                  })}
                </ul>
              </div>
              {error ? <p className="text-sm font-medium text-primary">{error}</p> : null}
              <div className="flex flex-wrap gap-2 pt-2">
                <PrimaryButton className="min-w-[7rem]" type="submit" disabled={submitting}>
                  {submitting ? 'Creando…' : 'Crear proyecto'}
                </PrimaryButton>
                <button
                  type="button"
                  className="rounded-md border border-black/15 bg-white px-4 py-2 text-sm font-medium text-ink hover:bg-black/[0.04]"
                  disabled={submitting}
                  onClick={closeCreateModal}
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  )
}
