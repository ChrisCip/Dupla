import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { CreateProjectModal } from '../components/projects/CreateProjectModal'
import { ProjectsBoardView } from '../components/projects/ProjectsBoardView'
import { ProjectsListView } from '../components/projects/ProjectsListView'
import { PROJECT_CARD_MIME } from '../constants/projectsPage'
import {
  NEXT_WORKFLOW_PHASE,
  PREV_WORKFLOW_PHASE,
} from '../constants/workflowPhases'
import type { Project } from '../types/project'
import { useAuthStore } from '../store/authStore'
import type { ProjectKindValue } from '../constants/projectKind'

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
  const [projectKind, setProjectKind] = useState<ProjectKindValue>('RESIDENTIAL')
  const [createFiles, setCreateFiles] = useState<File[]>([])
  const [projectSearch, setProjectSearch] = useState('')
  const dragRef = useRef(false)

  const filteredProjects = useMemo(() => {
    const q = projectSearch.trim().toLowerCase()
    if (!q) return projects
    return projects.filter((p) => p.name.toLowerCase().includes(q))
  }, [projects, projectSearch])

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
    if (projectKind === 'TENDER' && createFiles.length === 0) {
      setError('Los proyectos de licitación requieren al menos un archivo al crear.')
      return
    }
    setSubmitting(true)
    try {
      const fd = new FormData()
      fd.append('name', name.trim())
      fd.append('client_name', client.trim())
      fd.append('project_kind', projectKind)
      if (role === 'GERENCIA' && createMembers.size > 0) {
        fd.append('member_user_uuids', JSON.stringify(Array.from(createMembers)))
      }
      for (const f of createFiles) {
        fd.append('files', f)
      }
      const res = await apiFetch('/api/projects', {
        method: 'POST',
        token,
        body: fd,
      })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        setError((j as { detail?: string }).detail ?? 'No se pudo crear el proyecto')
        return
      }
      setFeedback('Proyecto creado. Ábrelo en la tabla o en el tablero, o crea otro.')
      if (feedbackClearRef.current) clearTimeout(feedbackClearRef.current)
      feedbackClearRef.current = setTimeout(() => setFeedback(null), 6000)
      setName('Nuevo proyecto')
      setClient('')
      setProjectKind('RESIDENTIAL')
      setCreateFiles([])
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
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold text-ink">Proyectos</h1>
          <p className="mt-1 text-sm text-muted">
            {role === 'GERENCIA'
              ? 'Tablero de proyectos. Arrastra una tarjeta a la columna de al lado para ir a la fase anterior o siguiente.'
              : 'Proyectos a los que tienes acceso.'}
          </p>
          <label className="mt-3 block max-w-md">
            <span className="sr-only">Buscar proyecto por nombre</span>
            <input
              type="search"
              className="du-input w-full"
              placeholder="Buscar por nombre…"
              value={projectSearch}
              onChange={(e) => setProjectSearch(e.target.value)}
              autoComplete="off"
              aria-label="Buscar proyecto por nombre"
            />
          </label>
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
        <ProjectsListView
          loadingList={loadingList}
          projects={projects}
          filteredProjects={filteredProjects}
          projectSearch={projectSearch}
          role={role}
          onOpenCreate={() => setCreateModalOpen(true)}
          onNavigateProject={(uuid) => navigate(`/app/projects/${uuid}`)}
        />
      ) : (
        <ProjectsBoardView
          loadingList={loadingList}
          projects={projects}
          filteredProjects={filteredProjects}
          projectSearch={projectSearch}
          boardMsg={boardMsg}
          role={role}
          onOpenCreate={() => setCreateModalOpen(true)}
          onDropOnPhaseColumn={onDropOnPhaseColumn}
          onDragOverBoard={onDragOverBoard}
          onDragStartProject={onDragStartProject}
          onDragEndBoard={onDragEndBoard}
          onOpenCard={openCard}
        />
      )}

      {createModalOpen && role === 'GERENCIA' ? (
        <CreateProjectModal
          onClose={closeCreateModal}
          onSubmit={createProject}
          name={name}
          setName={setName}
          client={client}
          setClient={setClient}
          projectKind={projectKind}
          setProjectKind={setProjectKind}
          createFiles={createFiles}
          setCreateFiles={setCreateFiles}
          createMembers={createMembers}
          setCreateMembers={setCreateMembers}
          adminUsersCreate={adminUsersCreate}
          userUuid={userUuid}
          error={error}
          submitting={submitting}
        />
      ) : null}
    </div>
  )
}
