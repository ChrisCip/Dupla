import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { Card } from '../components/Card'
import { PliegoCondicionesForm } from '../components/PliegoCondicionesForm'
import { PrimaryButton } from '../components/PrimaryButton'
import { StatusBadge } from '../components/StatusBadge'
import { Tabs } from '../components/Tabs'
import { TaskboardView } from '../components/TaskboardView'
import { PLAN_DELIVERY_STATUS_OPTIONS } from '../constants/planDeliveryStatus'
import { projectWorkspaceTabs } from '../constants/projectWorkspaceTabs'
import { NEXT_WORKFLOW_PHASE, WORKFLOW_PHASE_LABELS } from '../constants/workflowPhases'
import { mergePliegoItemStates } from '../lib/pliegoFormState'
import { useAuthStore } from '../store/authStore'
import { useWorkspaceStore } from '../store/workspaceStore'
import type { PlanDeliveryRow } from '../types/planDelivery'
import type { PliegoItemState } from '../types/pliegoForm'
import type { BootstrapCriterion, Project } from '../types/project'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function filenameFromContentDisposition(res: Response, fallback: string) {
  const cd = res.headers.get('content-disposition')
  if (!cd) return fallback
  const star = /filename\*=UTF-8''([^;\s]+)/i.exec(cd)
  if (star?.[1]) {
    try {
      return decodeURIComponent(star[1].trim())
    } catch {
      return fallback
    }
  }
  const quoted = /filename="([^"]+)"/i.exec(cd)
  if (quoted?.[1]) return quoted[1]
  const plain = /filename=([^;\s]+)/i.exec(cd)
  if (plain?.[1]) return plain[1].replace(/^"|"$/g, '')
  return fallback
}

type ProjectEventRow = {
  uuid: string
  event_type: string
  payload: Record<string, unknown>
  actor_user_uuid: string | null
  created_at: string
}

type ProjectFileRow = {
  uuid: string
  original_name: string
  mime: string | null
  category: string | null
  created_at: string
}

type RevisionRow = {
  uuid: string
  version: number
  decision: string
  notes: string | null
  created_at: string
}

type SubcontractLine = {
  uuid: string
  item_label: string
  provider: string | null
  price: string
  currency: string
}

type SubcontractQuoteRow = {
  uuid: string
  title: string | null
  created_at: string
  lines: SubcontractLine[]
}

function budgetPipeline(meta: Record<string, unknown>): Record<string, unknown> {
  const bp = meta.budget_pipeline
  return typeof bp === 'object' && bp !== null ? { ...(bp as Record<string, unknown>) } : {}
}

export function ProjectWorkspacePage() {
  const { projectUuid = '' } = useParams()
  const token = useAuthStore((s) => s.token)
  const role = useAuthStore((s) => s.role)
  const load = useWorkspaceStore((s) => s.load)
  const reset = useWorkspaceStore((s) => s.reset)
  const data = useWorkspaceStore((s) => s.data)
  const status = useWorkspaceStore((s) => s.status)
  const lastSavedAt = useWorkspaceStore((s) => s.lastSavedAt)
  const lastError = useWorkspaceStore((s) => s.lastError)
  const addGroup = useWorkspaceStore((s) => s.addGroup)
  const addItem = useWorkspaceStore((s) => s.addItem)
  const updateItem = useWorkspaceStore((s) => s.updateItem)
  const addMaterial = useWorkspaceStore((s) => s.addMaterial)
  const updateMaterial = useWorkspaceStore((s) => s.updateMaterial)
  const removeMaterial = useWorkspaceStore((s) => s.removeMaterial)

  const [tab, setTab] = useState<string>('detalles')
  const [kind, setKind] = useState<'tirada' | 'plano' | 'fase'>('fase')
  const [title, setTitle] = useState('Nueva sección')
  const [project, setProject] = useState<Project | null>(null)
  const [projectError, setProjectError] = useState<string | null>(null)
  const [flowMsg, setFlowMsg] = useState<string | null>(null)
  const [flowBusy, setFlowBusy] = useState(false)
  const [bootstrapDraft, setBootstrapDraft] = useState<BootstrapCriterion[]>([])
  const [specSummary, setSpecSummary] = useState('')
  const [pliegoItemStates, setPliegoItemStates] = useState<Record<string, PliegoItemState>>(() =>
    mergePliegoItemStates(undefined),
  )
  const [specSaveBusy, setSpecSaveBusy] = useState(false)
  const [files, setFiles] = useState<ProjectFileRow[]>([])
  const [revisions, setRevisions] = useState<RevisionRow[]>([])
  const [events, setEvents] = useState<ProjectEventRow[]>([])
  const [quotes, setQuotes] = useState<SubcontractQuoteRow[]>([])
  const [revDecision, setRevDecision] = useState('APPROVED')
  const [revNotes, setRevNotes] = useState('')
  const [fileCategory, setFileCategory] = useState('')
  const [bpDraft, setBpDraft] = useState<Record<string, unknown>>({})
  const [clientVersion, setClientVersion] = useState('')
  const [newQuoteTitle, setNewQuoteTitle] = useState('')
  const [lineItem, setLineItem] = useState('')
  const [linePrice, setLinePrice] = useState('')
  const [activeQuote, setActiveQuote] = useState('')
  const [exportBusy, setExportBusy] = useState<string | null>(null)
  const [memberRows, setMemberRows] = useState<{ uuid: string; email: string }[]>([])
  const [adminUsers, setAdminUsers] = useState<{ uuid: string; email: string }[]>([])
  const [membersBusy, setMembersBusy] = useState(false)
  const [membersMsg, setMembersMsg] = useState<string | null>(null)
  const [memberSelection, setMemberSelection] = useState<Set<string>>(new Set())
  const [planDeliveryRows, setPlanDeliveryRows] = useState<PlanDeliveryRow[]>([])
  const [planDeliveryMsg, setPlanDeliveryMsg] = useState<string | null>(null)

  const workspaceTabs = useMemo(
    () => projectWorkspaceTabs(project?.workflow_phase ?? 'BOOTSTRAPPING'),
    [project?.workflow_phase],
  )

  const refreshProject = useCallback(async () => {
    if (!projectUuid || !token) return
    setProjectError(null)
    const res = await apiFetch(`/api/projects/${projectUuid}`, { token })
    if (!res.ok) {
      setProjectError('No se pudieron cargar los datos del proyecto')
      return
    }
    const body = (await res.json()) as Project
    setProject(body)
    setBootstrapDraft(body.project_bootstrap_criteria ?? [])
    const spec = body.specifications_document ?? {}
    setSpecSummary(typeof spec.summary === 'string' ? spec.summary : '')
    const ga = spec.ga_fo_01_arquitectura
    const rawPliegoStates =
      ga && typeof ga === 'object' && ga !== null && 'item_states' in ga
        ? (ga as { item_states?: Record<string, unknown> }).item_states
        : undefined
    setPliegoItemStates(mergePliegoItemStates(rawPliegoStates))
    setBpDraft(budgetPipeline(body.workflow_meta ?? {}))
    setClientVersion(
      typeof budgetPipeline(body.workflow_meta ?? {}).client_approved_version_label === 'string'
        ? (budgetPipeline(body.workflow_meta ?? {}).client_approved_version_label as string)
        : '',
    )
  }, [projectUuid, token])

  useEffect(() => {
    if (!projectUuid) return
    void load(projectUuid)
    return () => reset()
  }, [load, projectUuid, reset])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      await refreshProject()
      if (cancelled) return
    })()
    return () => {
      cancelled = true
    }
  }, [refreshProject])

  const loadAuxLists = useCallback(async () => {
    if (!token || !projectUuid) return
    const [fe, fr, fq, ev] = await Promise.all([
      apiFetch(`/api/projects/${projectUuid}/files`, { token }),
      apiFetch(`/api/projects/${projectUuid}/architecture-revisions`, { token }),
      apiFetch(`/api/projects/${projectUuid}/subcontracts`, { token }),
      apiFetch(`/api/projects/${projectUuid}/events`, { token }),
    ])
    if (fe.ok) setFiles((await fe.json()) as ProjectFileRow[])
    if (fr.ok) setRevisions((await fr.json()) as RevisionRow[])
    if (fq.ok) setQuotes((await fq.json()) as SubcontractQuoteRow[])
    if (ev.ok) setEvents((await ev.json()) as ProjectEventRow[])
  }, [token, projectUuid])

  const loadPlanDelivery = useCallback(async () => {
    if (!token || !projectUuid) return
    setPlanDeliveryMsg(null)
    const res = await apiFetch(`/api/projects/${projectUuid}/plan-delivery-requests`, { token })
    if (!res.ok) {
      setPlanDeliveryMsg('No se pudo cargar el control de entrega de planos')
      return
    }
    setPlanDeliveryRows((await res.json()) as PlanDeliveryRow[])
  }, [token, projectUuid])

  async function addPlanDeliveryRow() {
    if (!token || !projectUuid) return
    setPlanDeliveryMsg(null)
    const res = await apiFetch(`/api/projects/${projectUuid}/plan-delivery-requests`, {
      method: 'POST',
      token,
      body: JSON.stringify({ description: '', status: 'SOLICITADO' }),
    })
    if (!res.ok) {
      setPlanDeliveryMsg('No se pudo crear la solicitud')
      return
    }
    const row = (await res.json()) as PlanDeliveryRow
    setPlanDeliveryRows((prev) => [...prev, row])
  }

  async function patchPlanDeliveryRow(rowUuid: string, patch: Record<string, unknown>) {
    if (!token || !projectUuid) return
    const res = await apiFetch(`/api/projects/${projectUuid}/plan-delivery-requests/${rowUuid}`, {
      method: 'PATCH',
      token,
      body: JSON.stringify(patch),
    })
    if (!res.ok) {
      setPlanDeliveryMsg('No se pudo guardar el registro')
      return
    }
    const updated = (await res.json()) as PlanDeliveryRow
    setPlanDeliveryRows((prev) => prev.map((r) => (r.uuid === rowUuid ? updated : r)))
  }

  async function deletePlanDeliveryRow(rowUuid: string) {
    if (!token || !projectUuid) return
    setPlanDeliveryMsg(null)
    const res = await apiFetch(`/api/projects/${projectUuid}/plan-delivery-requests/${rowUuid}`, {
      method: 'DELETE',
      token,
    })
    if (!res.ok) {
      setPlanDeliveryMsg('No se pudo eliminar el registro')
      return
    }
    setPlanDeliveryRows((prev) => prev.filter((r) => r.uuid !== rowUuid))
  }

  useEffect(() => {
    if (!projectUuid || !token) return
    if (
      tab === 'archivos' ||
      tab === 'revisiones' ||
      tab === 'presupuesto' ||
      tab === 'eventos'
    ) {
      void loadAuxLists()
    }
  }, [tab, projectUuid, token, loadAuxLists])

  useEffect(() => {
    if (tab !== 'entregaPlanos' || !projectUuid || !token) return
    void loadPlanDelivery()
  }, [tab, projectUuid, token, loadPlanDelivery])

  useEffect(() => {
    const ids = new Set(workspaceTabs.map((t) => t.id))
    if (!ids.has(tab)) {
      setTab(workspaceTabs[0]?.id ?? 'detalles')
    }
  }, [workspaceTabs, tab])

  useEffect(() => {
    if (!token || !projectUuid || role !== 'GERENCIA' || !project) return
    let cancelled = false
    void (async () => {
      const [m, u] = await Promise.all([
        apiFetch(`/api/projects/${projectUuid}/members`, { token }),
        apiFetch('/api/admin/users', { token }),
      ])
      if (cancelled) return
      if (m.ok) setMemberRows((await m.json()) as { uuid: string; email: string }[])
      if (u.ok) setAdminUsers((await u.json()) as { uuid: string; email: string }[])
    })()
    return () => {
      cancelled = true
    }
  }, [token, projectUuid, role, project])

  useEffect(() => {
    const creator = project?.created_by_user_uuid
    if (!creator) return
    const next = new Set(
      memberRows.map((r) => r.uuid).filter((id) => id !== creator),
    )
    setMemberSelection(next)
  }, [memberRows, project?.created_by_user_uuid])

  async function exportFile(path: string, filename: string, busyKey: string) {
    if (!token) return
    setExportBusy(busyKey)
    try {
      const res = await apiFetch(path, { token })
      if (!res.ok) return
      const blob = await res.blob()
      downloadBlob(blob, filenameFromContentDisposition(res, filename))
    } finally {
      setExportBusy(null)
    }
  }

  async function advancePhase() {
    if (!token || !project) return
    const next = NEXT_WORKFLOW_PHASE[project.workflow_phase]
    if (!next) return
    setFlowMsg(null)
    setFlowBusy(true)
    try {
      const res = await apiFetch(`/api/projects/${projectUuid}/transitions`, {
        method: 'POST',
        token,
        body: JSON.stringify({ target_phase: next }),
      })
      const j = await res.json().catch(() => ({}))
      if (!res.ok) {
        setFlowMsg((j as { detail?: string }).detail ?? 'No se pudo avanzar la fase')
        return
      }
      setProject(j as Project)
      await loadAuxLists()
    } finally {
      setFlowBusy(false)
    }
  }

  async function saveBootstrap() {
    if (!token) return
    setFlowMsg(null)
    const res = await apiFetch(`/api/projects/${projectUuid}/bootstrap`, {
      method: 'PUT',
      token,
      body: JSON.stringify({ criteria: bootstrapDraft }),
    })
    const j = await res.json().catch(() => ({}))
    if (!res.ok) {
      setFlowMsg((j as { detail?: string }).detail ?? 'Error al guardar checklist')
      return
    }
    setProject(j as Project)
  }

  async function saveSpecifications() {
    if (!token || !project) return
    setFlowMsg(null)
    setSpecSaveBusy(true)
    try {
      const doc = {
        ...project.specifications_document,
        summary: specSummary,
        ga_fo_01_arquitectura: {
          schema_version: 1 as const,
          item_states: pliegoItemStates,
        },
      }
      const res = await apiFetch(`/api/projects/${projectUuid}/specifications`, {
        method: 'PUT',
        token,
        body: JSON.stringify({ document: doc }),
      })
      const j = await res.json().catch(() => ({}))
      if (!res.ok) {
        setFlowMsg((j as { detail?: string }).detail ?? 'Error al guardar el pliego de condiciones')
        return
      }
      setProject(j as Project)
    } finally {
      setSpecSaveBusy(false)
    }
  }

  async function saveBudgetPipeline() {
    if (!token) return
    setFlowMsg(null)
    const bp = { ...bpDraft, client_approved_version_label: clientVersion || null }
    const res = await apiFetch(`/api/projects/${projectUuid}/workflow-meta`, {
      method: 'PATCH',
      token,
      body: JSON.stringify({ budget_pipeline: bp }),
    })
    const j = await res.json().catch(() => ({}))
    if (!res.ok) {
      setFlowMsg((j as { detail?: string }).detail ?? 'Error al guardar presupuesto')
      return
    }
    setProject(j as Project)
    setBpDraft(budgetPipeline((j as Project).workflow_meta ?? {}))
  }

  async function submitRevision() {
    if (!token) return
    setFlowMsg(null)
    const res = await apiFetch(`/api/projects/${projectUuid}/architecture-revisions`, {
      method: 'POST',
      token,
      body: JSON.stringify({
        decision: revDecision,
        notes: revNotes.trim() || null,
        checklist: {},
      }),
    })
    const j = await res.json().catch(() => ({}))
    if (!res.ok) {
      setFlowMsg((j as { detail?: string }).detail ?? 'Error al registrar revisión')
      return
    }
    setRevNotes('')
    await loadAuxLists()
  }

  async function uploadFileList(f: FileList | null) {
    if (!token || !f?.[0]) return
    setFlowMsg(null)
    const fd = new FormData()
    fd.append('file', f[0])
    if (fileCategory.trim()) fd.append('category', fileCategory.trim())
    const res = await apiFetch(`/api/projects/${projectUuid}/files`, {
      method: 'POST',
      token,
      body: fd,
    })
    const j = await res.json().catch(() => ({}))
    if (!res.ok) {
      setFlowMsg((j as { detail?: string }).detail ?? 'Error al subir archivo')
      return
    }
    await loadAuxLists()
    await refreshProject()
  }

  async function openProjectChat() {
    if (!token) return
    const res = await apiFetch(`/api/projects/${projectUuid}/chat/conversation`, {
      method: 'POST',
      token,
    })
    const j = await res.json().catch(() => ({}))
    if (!res.ok) return
    const uuid = (j as { uuid?: string }).uuid
    if (uuid) window.location.assign(`/app/chat?conversation=${encodeURIComponent(uuid)}`)
  }

  const displayTitle = project?.name ?? 'Proyecto'
  const phaseLabel = project ? WORKFLOW_PHASE_LABELS[project.workflow_phase] ?? project.workflow_phase : ''
  const nextPhase = project ? NEXT_WORKFLOW_PHASE[project.workflow_phase] : undefined

  return (
    <>
      <div className="mb-8 flex flex-col gap-6 border-b border-black/10 pb-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="du-meta">
            <Link className="du-link text-sm" to="/app/projects">
              ← Volver a proyectos
            </Link>
          </div>
          <h1 id="workspace-heading" className="mt-2 text-xl font-bold tracking-tight text-ink">
            {displayTitle}
          </h1>
          <p className="mt-1 du-meta">
            {phaseLabel ? `Fase: ${phaseLabel}` : 'Cargando fase…'}
          </p>
        </div>
        <div className="flex w-full flex-col gap-4 sm:w-auto sm:items-end">
          <StatusBadge status={status} lastSavedAt={lastSavedAt} errorMessage={lastError} />
          <details className="w-full max-w-md rounded-md border border-black/10 bg-white px-3 py-2 text-left text-sm shadow-[var(--shadow-card)] sm:max-w-lg">
            <summary className="cursor-pointer font-medium text-ink">Exportaciones (Excel / PDF)</summary>
            <p className="mt-2 text-xs text-muted">
              Pueden tardar unos segundos; el botón muestra «Generando…» mientras descarga.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <PrimaryButton
                type="button"
                disabled={exportBusy !== null}
                onClick={() =>
                  void exportFile(
                    `/api/projects/${projectUuid}/exports/pliego.xlsx`,
                    `pliego-${projectUuid}.xlsx`,
                    'pliego-xlsx',
                  )
                }
              >
                {exportBusy === 'pliego-xlsx' ? 'Generando…' : 'Pliego (Excel)'}
              </PrimaryButton>
              <PrimaryButton
                type="button"
                disabled={exportBusy !== null}
                onClick={() =>
                  void exportFile(
                    `/api/projects/${projectUuid}/exports/pliego.pdf`,
                    `pliego-${projectUuid}.pdf`,
                    'pliego-pdf',
                  )
                }
              >
                {exportBusy === 'pliego-pdf' ? 'Generando…' : 'Pliego (PDF)'}
              </PrimaryButton>
              <PrimaryButton
                type="button"
                disabled={exportBusy !== null}
                onClick={() =>
                  void exportFile(
                    `/api/projects/${projectUuid}/exports/control-planos.xlsx`,
                    `control-planos-${projectUuid}.xlsx`,
                    'control-xlsx',
                  )
                }
              >
                {exportBusy === 'control-xlsx' ? 'Generando…' : 'Control planos (Excel)'}
              </PrimaryButton>
              <PrimaryButton
                type="button"
                disabled={exportBusy !== null}
                onClick={() =>
                  void exportFile(
                    `/api/projects/${projectUuid}/exports/control-planos.pdf`,
                    `control-planos-${projectUuid}.pdf`,
                    'control-pdf',
                  )
                }
              >
                {exportBusy === 'control-pdf' ? 'Generando…' : 'Control planos (PDF)'}
              </PrimaryButton>
            </div>
          </details>
        </div>
      </div>

      {projectUuid ? (
        <div className="mb-6 space-y-4">
          <Card className="overflow-hidden p-0">
            <div className="border-b border-black/10 bg-black/2 px-4 py-2">
              <h2 className="text-sm font-semibold text-ink">Tareas del proyecto</h2>
              <p className="du-meta mt-0.5">Arrastra tarjetas entre columnas; abre una tarea para editar o comentar.</p>
            </div>
            <div className="min-h-[min(420px,55vh)] min-w-0">
              <TaskboardView projectUuid={projectUuid} variant="embedded" />
            </div>
          </Card>
          <Card className="p-4">
            <h2 className="text-sm font-semibold text-ink">Acciones rápidas</h2>
            <p className="mt-1 text-xs text-muted">
              Atajos al tablero completo, chat del proyecto y a la pestaña Flujo (avance de fase sin duplicar controles
              aquí).
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link
                className="du-pill-action"
                to={`/app/tasks?project_uuid=${encodeURIComponent(projectUuid)}`}
              >
                Tablero completo
              </Link>
              <button type="button" className="du-pill-action" onClick={() => void openProjectChat()}>
                Chat del proyecto
              </button>
              <button type="button" className="du-pill-action" onClick={() => setTab('flujo')}>
                Ir a Flujo
              </button>
            </div>
          </Card>
        </div>
      ) : null}

      <Tabs tabs={workspaceTabs} value={tab} onChange={setTab} labelledBy="workspace-heading">
        {tab === 'detalles' ? (
          <Card className="p-6">
            <h2 className="text-lg font-semibold text-ink">Detalles del proyecto</h2>
            {projectError ? <p className="mt-3 text-sm text-primary">{projectError}</p> : null}
            {!project && !projectError ? (
              <p className="mt-3 text-sm text-muted">Cargando…</p>
            ) : null}
            {project ? (
              <>
                <dl className="mt-6 grid gap-4 sm:grid-cols-2">
                  <div>
                    <dt className="du-meta">Nombre</dt>
                    <dd className="mt-1 text-sm font-medium text-ink">{project.name}</dd>
                  </div>
                  <div>
                    <dt className="du-meta">Cliente</dt>
                    <dd className="mt-1 text-sm text-ink">{project.client_name ?? '—'}</dd>
                  </div>
                  <div>
                    <dt className="du-meta">Estado legado</dt>
                    <dd className="mt-1 text-sm text-ink">{project.status}</dd>
                  </div>
                  <div>
                    <dt className="du-meta">Fase del flujo</dt>
                    <dd className="mt-1 text-sm font-medium text-ink">{phaseLabel}</dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="du-meta">Identificador</dt>
                    <dd className="mt-1 font-mono text-xs text-muted">{project.uuid}</dd>
                  </div>
                </dl>
                <div className="mt-6 flex flex-wrap gap-2">
                  <Link
                    className="du-pill-action"
                    to={`/app/tasks?project_uuid=${encodeURIComponent(project.uuid)}`}
                  >
                    Tablero del proyecto
                  </Link>
                  <button type="button" className="du-pill-action" onClick={() => void openProjectChat()}>
                    Chat del proyecto
                  </button>
                </div>
                {role === 'GERENCIA' ? (
                  <div className="mt-8 border-t border-black/10 pt-6">
                    <h3 className="text-md font-semibold text-ink">Quién puede ver este proyecto</h3>
                    <p className="mt-1 text-sm text-muted">
                      El creador del proyecto siempre tiene acceso. Marca usuarios con módulo Arquitectura que deben ver
                      el workspace.
                    </p>
                    {membersMsg ? <p className="mt-2 text-sm text-primary">{membersMsg}</p> : null}
                    <ul className="mt-4 max-h-56 space-y-2 overflow-y-auto rounded-md border border-black/10 p-3 text-sm">
                      {adminUsers.map((u) => {
                        const isCreator = u.uuid === project.created_by_user_uuid
                        const checked = isCreator || memberSelection.has(u.uuid)
                        return (
                          <li key={u.uuid} className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              id={`pm-${u.uuid}`}
                              className="mt-0.5"
                              checked={checked}
                              disabled={isCreator || membersBusy}
                              onChange={() => {
                                if (isCreator) return
                                setMemberSelection((prev) => {
                                  const next = new Set(prev)
                                  if (next.has(u.uuid)) next.delete(u.uuid)
                                  else next.add(u.uuid)
                                  return next
                                })
                              }}
                            />
                            <label htmlFor={`pm-${u.uuid}`} className={isCreator ? 'text-muted' : 'text-ink'}>
                              {u.email}
                              {isCreator ? <span className="du-meta"> (creador)</span> : null}
                            </label>
                          </li>
                        )
                      })}
                    </ul>
                    <PrimaryButton
                      type="button"
                      className="mt-4"
                      disabled={membersBusy}
                      onClick={() => {
                        if (!token || !projectUuid) return
                        setMembersBusy(true)
                        setMembersMsg(null)
                        void (async () => {
                          try {
                            const res = await apiFetch(`/api/projects/${projectUuid}/members`, {
                              method: 'PUT',
                              token,
                              body: JSON.stringify({
                                member_user_uuids: Array.from(memberSelection),
                              }),
                            })
                            if (!res.ok) {
                              setMembersMsg('No se pudo guardar la lista de miembros')
                              return
                            }
                            setMembersMsg('Lista de acceso actualizada')
                            const m = await apiFetch(`/api/projects/${projectUuid}/members`, { token })
                            if (m.ok) {
                              setMemberRows((await m.json()) as { uuid: string; email: string }[])
                            }
                          } finally {
                            setMembersBusy(false)
                          }
                        })()
                      }}
                    >
                      {membersBusy ? 'Guardando…' : 'Guardar acceso'}
                    </PrimaryButton>
                  </div>
                ) : null}
              </>
            ) : null}
          </Card>
        ) : null}

        {tab === 'flujo' ? (
          <Card className="space-y-4 p-6">
            <h2 className="text-lg font-semibold text-ink">Flujo de trabajo</h2>
            {project ? (
              <>
                <p className="rounded-md border border-black/10 bg-black/[0.02] px-3 py-2 text-sm text-muted">
                  Fase actual:{' '}
                  <span className="font-semibold text-ink">{phaseLabel}</span>. Avanza solo cuando el trabajo de esta
                  etapa esté hecho; si el botón falla, el mensaje de arriba indica el motivo.
                </p>
                {flowMsg ? <p className="text-sm text-primary">{flowMsg}</p> : null}
                {project.workflow_phase === 'BOOTSTRAPPING' ? (
                  <div className="space-y-3 border-t border-black/10 pt-4">
                    <p className="text-sm font-medium text-ink">Checklist de documentos</p>
                    <ul className="space-y-2">
                      {bootstrapDraft.map((c, i) => (
                        <li key={c.id} className="flex items-start gap-2 text-sm">
                          <input
                            type="checkbox"
                            className="mt-1"
                            checked={!!c.done}
                            onChange={(e) => {
                              const next = [...bootstrapDraft]
                              next[i] = { ...next[i], done: e.target.checked }
                              setBootstrapDraft(next)
                            }}
                          />
                          <span>
                            {c.label}
                            {c.required ? <span className="text-primary"> *</span> : null}
                          </span>
                        </li>
                      ))}
                    </ul>
                    <PrimaryButton type="button" onClick={() => void saveBootstrap()}>
                      Guardar checklist
                    </PrimaryButton>
                  </div>
                ) : null}
                {nextPhase ? (
                  <PrimaryButton type="button" disabled={flowBusy} onClick={() => void advancePhase()}>
                    {flowBusy
                      ? 'Procesando…'
                      : `Avanzar a: ${WORKFLOW_PHASE_LABELS[nextPhase] ?? nextPhase}`}
                  </PrimaryButton>
                ) : (
                  <p className="text-sm text-muted">El proyecto completó el flujo definido.</p>
                )}
                {nextPhase === 'BUDGET_APPROVED' && role !== 'GERENCIA' ? (
                  <p className="text-sm text-primary">
                    Solo un usuario de Gerencia puede marcar la aprobación final del presupuesto.
                  </p>
                ) : null}
              </>
            ) : (
              <p className="text-sm text-muted">Cargando…</p>
            )}
          </Card>
        ) : null}

        {tab === 'archivos' ? (
          <Card className="space-y-4 p-6">
            <h2 className="text-lg font-semibold text-ink">Archivos / planos</h2>
            <p className="text-sm text-muted">Sube DWG/DXF u otros adjuntos. Categoría opcional (nomenclatura).</p>
            {flowMsg ? <p className="text-sm text-primary">{flowMsg}</p> : null}
            <label className="block text-sm text-muted">
              Categoría
              <input
                className="du-input mt-1"
                value={fileCategory}
                onChange={(e) => setFileCategory(e.target.value)}
              />
            </label>
            <input
              type="file"
              className="text-sm"
              onChange={(e) => void uploadFileList(e.target.files)}
            />
            <ul className="divide-y divide-black/10 text-sm">
              {files.map((f) => (
                <li key={f.uuid} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <span>{f.original_name}</span>
                  <a
                    className="font-semibold text-primary underline-offset-2 hover:underline"
                    href={`/api/projects/${projectUuid}/files/${f.uuid}/download`}
                    onClick={async (e) => {
                      e.preventDefault()
                      if (!token) return
                      const res = await apiFetch(
                        `/api/projects/${projectUuid}/files/${f.uuid}/download`,
                        { token },
                      )
                      if (!res.ok) return
                      const blob = await res.blob()
                      downloadBlob(blob, f.original_name)
                    }}
                  >
                    Descargar
                  </a>
                </li>
              ))}
            </ul>
            {files.length === 0 ? <p className="text-sm text-muted">Sin archivos.</p> : null}
          </Card>
        ) : null}

        {tab === 'entregaPlanos' ? (
          <Card className="space-y-4 p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-ink">Control entrega de planos</h2>
                <p className="mt-1 max-w-2xl text-sm text-muted">
                  Registro tipo GA-FO-03. Cada solicitud recibe un número <span className="font-mono">SDP NNNN</span>{' '}
                  único en este proyecto. La columna «Cantidad días» muestra el valor registrado o la diferencia entre
                  fechas de solicitud y entrega.
                </p>
              </div>
              <PrimaryButton
                type="button"
                disabled={!token || !projectUuid}
                onClick={() => void addPlanDeliveryRow()}
              >
                Nueva solicitud
              </PrimaryButton>
            </div>
            {planDeliveryMsg ? <p className="text-sm text-primary">{planDeliveryMsg}</p> : null}
            <div className="overflow-x-auto rounded border border-black/10">
              <table className="w-full min-w-[960px] text-left text-sm">
                <thead className="bg-black/[0.04] text-xs uppercase text-muted">
                  <tr>
                    <th className="px-3 py-2">No.</th>
                    <th className="px-3 py-2">Fecha solicitud</th>
                    <th className="px-3 py-2">Proyecto</th>
                    <th className="px-3 py-2">No. solicitud</th>
                    <th className="px-3 py-2">Descripción</th>
                    <th className="px-3 py-2">Fecha entrega</th>
                    <th className="px-3 py-2">Cant. días</th>
                    <th className="px-3 py-2">Estado</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {planDeliveryRows.map((row, idx) => (
                    <tr key={row.uuid} className="border-t border-black/5 odd:bg-black/[0.015]">
                      <td className="px-3 py-2 align-top tabular-nums text-muted">{idx + 1}</td>
                      <td className="px-3 py-2 align-top">
                        <input
                          type="date"
                          className="du-input w-[10.5rem] py-1.5 text-sm"
                          value={row.request_date ? row.request_date.slice(0, 10) : ''}
                          onChange={(e) => {
                            const v = e.target.value
                            void patchPlanDeliveryRow(row.uuid, {
                              request_date: v ? v : null,
                            })
                          }}
                          aria-label="Fecha de solicitud"
                        />
                      </td>
                      <td className="px-3 py-2 align-top text-sm text-ink">{project?.name ?? '—'}</td>
                      <td className="px-3 py-2 align-top font-mono text-xs text-ink">{row.request_number}</td>
                      <td className="px-3 py-2 align-top">
                        <input
                          className="du-input min-w-[200px] py-1.5 text-sm"
                          value={row.description}
                          onChange={(e) => {
                            const v = e.target.value
                            setPlanDeliveryRows((prev) =>
                              prev.map((r) => (r.uuid === row.uuid ? { ...r, description: v } : r)),
                            )
                          }}
                          onBlur={(e) => {
                            const v = e.target.value.trim()
                            void patchPlanDeliveryRow(row.uuid, { description: v })
                          }}
                          aria-label="Descripción"
                        />
                      </td>
                      <td className="px-3 py-2 align-top">
                        <input
                          type="date"
                          className="du-input w-[10.5rem] py-1.5 text-sm"
                          value={row.delivery_date ? row.delivery_date.slice(0, 10) : ''}
                          onChange={(e) => {
                            const v = e.target.value
                            void patchPlanDeliveryRow(row.uuid, {
                              delivery_date: v ? v : null,
                            })
                          }}
                          aria-label="Fecha de entrega"
                        />
                      </td>
                      <td className="px-3 py-2 align-top">
                        <input
                          type="number"
                          min={0}
                          className="du-input w-20 py-1.5 text-sm"
                          placeholder="Auto"
                          defaultValue={row.days_count ?? ''}
                          key={`${row.uuid}-days-${row.updated_at}`}
                          onBlur={(e) => {
                            const raw = e.target.value.trim()
                            const n = raw === '' ? null : Number(raw)
                            void patchPlanDeliveryRow(row.uuid, {
                              days_count: n === null || Number.isNaN(n) ? null : n,
                            })
                          }}
                          aria-label="Cantidad de días"
                        />
                        {row.days_resolved != null ? (
                          <div className="du-meta mt-0.5">Calc: {row.days_resolved}</div>
                        ) : null}
                      </td>
                      <td className="px-3 py-2 align-top">
                        <select
                          className="du-input py-1.5 text-sm"
                          value={row.status}
                          onChange={(e) => void patchPlanDeliveryRow(row.uuid, { status: e.target.value })}
                          aria-label="Estado"
                        >
                          {PLAN_DELIVERY_STATUS_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>
                              {o.label}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="px-3 py-2 align-top">
                        <button
                          type="button"
                          className="text-sm font-medium text-primary underline-offset-2 hover:underline"
                          onClick={() => void deletePlanDeliveryRow(row.uuid)}
                        >
                          Eliminar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {planDeliveryRows.length === 0 ? (
              <p className="text-sm text-muted">No hay solicitudes. Usa «Nueva solicitud» para crear la primera.</p>
            ) : null}
          </Card>
        ) : null}

        {tab === 'revisiones' ? (
          <Card className="space-y-4 p-6">
            <h2 className="text-lg font-semibold text-ink">Revisiones de arquitectura</h2>
            <p className="text-sm text-muted">
              Puedes registrar una revisión en cualquier fase del proyecto. Para avanzar a «Pliego de condiciones» sigue
              siendo necesaria una revisión <span className="font-medium text-ink">aprobada</span> cuando el flujo esté
              en revisión de arquitectura.
            </p>
            {flowMsg ? <p className="text-sm text-primary">{flowMsg}</p> : null}
            <div className="space-y-3 border-b border-black/10 pb-4">
              <label className="block text-sm text-muted">
                Decisión
                <select
                  className="du-input mt-1"
                  value={revDecision}
                  onChange={(e) => setRevDecision(e.target.value)}
                >
                  <option value="APPROVED">APPROVED</option>
                  <option value="REJECTED">REJECTED</option>
                  <option value="PARTIAL">PARTIAL</option>
                </select>
              </label>
              <label className="block text-sm text-muted">
                Notas
                <textarea
                  className="du-input mt-1 min-h-[80px]"
                  value={revNotes}
                  onChange={(e) => setRevNotes(e.target.value)}
                />
              </label>
              <PrimaryButton type="button" onClick={() => void submitRevision()}>
                Registrar revisión
              </PrimaryButton>
            </div>
            <ul className="space-y-2 text-sm">
              {revisions.map((r) => (
                <li key={r.uuid} className="rounded border border-black/10 px-3 py-2">
                  <span className="font-medium">v{r.version}</span> · {r.decision}
                  {r.notes ? <p className="text-muted">{r.notes}</p> : null}
                </li>
              ))}
            </ul>
            {revisions.length === 0 ? <p className="text-sm text-muted">Sin revisiones.</p> : null}
          </Card>
        ) : null}

        {tab === 'especificaciones' ? (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-ink">Pliego de condiciones (GA-FO-01)</h2>
            <PliegoCondicionesForm
              projectUuid={projectUuid}
              token={token}
              specSummary={specSummary}
              onSpecSummaryChange={setSpecSummary}
              itemStates={pliegoItemStates}
              onItemStatesChange={setPliegoItemStates}
              onPersist={saveSpecifications}
              persistBusy={specSaveBusy}
              flowMsg={flowMsg}
            />
          </div>
        ) : null}

        {tab === 'presupuesto' ? (
          <div className="space-y-6">
            <Card className="space-y-4 p-6">
              <h2 className="text-lg font-semibold text-ink">Pipeline de presupuesto</h2>
              <p className="text-sm text-muted">
                Esta fase sigue al <strong className="text-ink">pliego de condiciones</strong>. Marca cada hito cuando
                corresponda y registra la versión aprobada por el cliente antes del cierre.
              </p>
              {flowMsg ? <p className="text-sm text-primary">{flowMsg}</p> : null}
              {(
                [
                  ['subcontracts_done', 'Cotizaciones de subcontratación listas'],
                  ['volumetry_done', 'Volumetría completada'],
                  ['cost_analysis_done', 'Análisis de costo completado'],
                  ['budget_marked_complete', 'Presupuesto interno completado'],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={!!bpDraft[key]}
                    onChange={(e) => setBpDraft((d) => ({ ...d, [key]: e.target.checked }))}
                  />
                  {label}
                </label>
              ))}
              <label className="block text-sm text-muted">
                Etiqueta de versión aprobada por el cliente
                <input
                  className="du-input mt-1"
                  value={clientVersion}
                  onChange={(e) => setClientVersion(e.target.value)}
                  placeholder="ej. v2"
                />
              </label>
              <PrimaryButton type="button" onClick={() => void saveBudgetPipeline()}>
                Guardar estado del pipeline
              </PrimaryButton>
            </Card>
            <Card className="space-y-4 p-6">
              <h3 className="text-md font-semibold text-ink">Cotizaciones</h3>
              <div className="flex flex-wrap gap-2">
                <input
                  className="du-input flex-1 min-w-[160px]"
                  placeholder="Título de cotización"
                  value={newQuoteTitle}
                  onChange={(e) => setNewQuoteTitle(e.target.value)}
                />
                <PrimaryButton
                  type="button"
                  onClick={async () => {
                    if (!token) return
                    const res = await apiFetch(`/api/projects/${projectUuid}/subcontracts`, {
                      method: 'POST',
                      token,
                      body: JSON.stringify({ title: newQuoteTitle.trim() || null }),
                    })
                    if (res.ok) {
                      setNewQuoteTitle('')
                      await loadAuxLists()
                    }
                  }}
                >
                  Nueva cotización
                </PrimaryButton>
              </div>
              <label className="block text-sm text-muted">
                Cotización activa para líneas
                <select
                  className="du-input mt-1"
                  value={activeQuote}
                  onChange={(e) => setActiveQuote(e.target.value)}
                >
                  <option value="">—</option>
                  {quotes.map((q) => (
                    <option key={q.uuid} value={q.uuid}>
                      {q.title ?? q.uuid.slice(0, 8)}
                    </option>
                  ))}
                </select>
              </label>
              <div className="flex flex-wrap gap-2">
                <input
                  className="du-input flex-1 min-w-[120px]"
                  placeholder="Ítem"
                  value={lineItem}
                  onChange={(e) => setLineItem(e.target.value)}
                />
                <input
                  className="du-input w-28"
                  placeholder="Precio"
                  type="number"
                  value={linePrice}
                  onChange={(e) => setLinePrice(e.target.value)}
                />
                <PrimaryButton
                  type="button"
                  disabled={!activeQuote}
                  onClick={async () => {
                    if (!token || !activeQuote) return
                    const res = await apiFetch(
                      `/api/projects/${projectUuid}/subcontracts/${activeQuote}/lines`,
                      {
                        method: 'POST',
                        token,
                        body: JSON.stringify({
                          item_label: lineItem.trim(),
                          price: Number(linePrice),
                          currency: 'MXN',
                        }),
                      },
                    )
                    if (res.ok) {
                      setLineItem('')
                      setLinePrice('')
                      await loadAuxLists()
                    }
                  }}
                >
                  Agregar línea
                </PrimaryButton>
              </div>
              {quotes.map((q) => (
                <div key={q.uuid} className="rounded border border-black/5 p-3 text-sm">
                  <div className="font-medium">{q.title ?? 'Sin título'}</div>
                  <ul className="mt-2 list-disc pl-5 text-muted">
                    {q.lines.map((l) => (
                      <li key={l.uuid}>
                        {l.item_label} — {l.price} {l.currency}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </Card>
          </div>
        ) : null}

        {tab === 'eventos' ? (
          <Card className="p-6">
            <h2 className="text-lg font-semibold text-ink">Eventos recientes</h2>
            <ul className="mt-4 space-y-2 text-sm">
              {events.map((ev) => (
                <li key={ev.uuid} className="rounded border border-black/5 px-3 py-2">
                  <span className="font-medium">{ev.event_type}</span>
                  <span className="du-meta ml-2">{new Date(ev.created_at).toLocaleString()}</span>
                  <pre className="mt-1 max-h-24 overflow-auto text-xs text-muted">
                    {JSON.stringify(ev.payload, null, 2)}
                  </pre>
                </li>
              ))}
            </ul>
            {events.length === 0 ? <p className="mt-4 text-sm text-muted">Sin eventos.</p> : null}
          </Card>
        ) : null}

        {tab === 'pliegos' ? (
          <div className="space-y-8">
            <Card className="p-4">
              <div className="text-sm font-semibold text-ink">Agregar sección</div>
              <p className="mt-1 text-sm text-muted">
                Las secciones agrupan ítems del pliego: <strong className="text-ink">tirada</strong>,{' '}
                <strong className="text-ink">plano</strong> o <strong className="text-ink">fase</strong>. Después usa «+
                Ítem» en cada bloque para las partidas.
              </p>
              <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-end">
                <label className="block text-sm text-muted">
                  Tipo
                  <select
                    className="du-input mt-1 md:w-56"
                    value={kind}
                    onChange={(e) => setKind(e.target.value as typeof kind)}
                  >
                    <option value="tirada">Tirada</option>
                    <option value="plano">Plano</option>
                    <option value="fase">Fase</option>
                  </select>
                </label>
                <label className="block flex-1 text-sm text-muted">
                  Título
                  <input
                    className="du-input mt-1"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    aria-label="Título de la sección"
                  />
                </label>
                <PrimaryButton type="button" onClick={() => addGroup(kind, title)}>
                  Agregar sección
                </PrimaryButton>
              </div>
            </Card>

            <div className="space-y-6">
              {data.groups.map((g) => (
                <Card key={g.id} className="overflow-hidden p-0">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-black/5 bg-white px-4 py-3">
                    <div>
                      <div className="text-xs uppercase tracking-wide text-muted">{g.kind}</div>
                      <div className="text-lg font-semibold text-ink">{g.title}</div>
                    </div>
                    <PrimaryButton type="button" onClick={() => addItem(g.id)}>
                      + Ítem
                    </PrimaryButton>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[900px] text-left text-sm">
                      <thead className="sticky top-0 z-10 bg-black/[0.04] text-xs uppercase text-muted">
                        <tr>
                          <th className="px-4 py-2">Partida</th>
                          <th className="px-4 py-2">Descripción</th>
                          <th className="px-4 py-2">Unidad</th>
                          <th className="px-4 py-2">Cantidad</th>
                          <th className="px-4 py-2">P. unitario</th>
                          <th className="px-4 py-2">Subtotal</th>
                          <th className="px-4 py-2">Notas</th>
                        </tr>
                      </thead>
                      <tbody>
                        {g.items.map((it) => (
                          <tr key={it.id} className="border-t border-black/5 odd:bg-black/[0.015]">
                            <td className="px-4 py-2 align-top">
                              <input
                                className="du-input w-28 py-1.5 text-sm"
                                value={it.partida ?? ''}
                                onChange={(e) => updateItem(g.id, it.id, { partida: e.target.value || null })}
                                aria-label="Partida"
                              />
                            </td>
                            <td className="px-4 py-2 align-top">
                              <input
                                className="du-input min-w-[240px] py-1.5 text-sm"
                                value={it.descripcion}
                                onChange={(e) => updateItem(g.id, it.id, { descripcion: e.target.value })}
                                aria-label="Descripción"
                              />
                            </td>
                            <td className="px-4 py-2 align-top">
                              <input
                                className="du-input w-20 py-1.5 text-sm"
                                value={it.unidad ?? ''}
                                onChange={(e) => updateItem(g.id, it.id, { unidad: e.target.value || null })}
                                aria-label="Unidad"
                              />
                            </td>
                            <td className="px-4 py-2 align-top">
                              <input
                                className="du-input w-24 py-1.5 text-sm"
                                type="number"
                                min={0}
                                step="any"
                                value={it.cantidad ?? ''}
                                onChange={(e) => {
                                  const v = e.target.value
                                  updateItem(g.id, it.id, {
                                    cantidad: v === '' ? 0 : Number(v),
                                  })
                                }}
                                aria-label="Cantidad"
                              />
                            </td>
                            <td className="px-4 py-2 align-top">
                              <input
                                className="du-input w-28 py-1.5 text-sm"
                                type="number"
                                min={0}
                                step="any"
                                value={it.precio_unitario ?? ''}
                                onChange={(e) => {
                                  const v = e.target.value
                                  updateItem(g.id, it.id, {
                                    precio_unitario: v === '' ? 0 : Number(v),
                                  })
                                }}
                                aria-label="Precio unitario"
                              />
                            </td>
                            <td className="px-4 py-2 align-top text-sm tabular-nums text-ink">
                              {(it.subtotal ?? 0).toLocaleString(undefined, {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })}
                            </td>
                            <td className="px-4 py-2 align-top">
                              <input
                                className="du-input w-44 py-1.5 text-sm"
                                value={it.notas ?? ''}
                                onChange={(e) => updateItem(g.id, it.id, { notas: e.target.value || null })}
                                aria-label="Notas"
                              />
                            </td>
                          </tr>
                        ))}
                        {g.items.length === 0 ? (
                          <tr>
                            <td className="px-4 py-6 text-sm text-muted" colSpan={7}>
                              No hay ítems en esta sección.
                            </td>
                          </tr>
                        ) : null}
                      </tbody>
                    </table>
                  </div>
                </Card>
              ))}

              {data.groups.length === 0 ? (
                <Card className="border-2 border-dashed border-black/12 bg-black/[0.02] p-10 text-center">
                  <p className="text-sm font-medium text-ink">Empieza por una sección</p>
                  <p className="mt-2 text-sm text-muted">
                    Elige tipo y título arriba y pulsa «Agregar sección». El tablero de ítems aparece dentro de cada
                    bloque.
                  </p>
                </Card>
              ) : null}
            </div>
          </div>
        ) : null}

        {tab === 'materiales' ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="max-w-prose text-sm text-muted">
                Cubicación e insumos. El total se calcula a partir de la cantidad estimada y el desperdicio (%).
              </p>
              <PrimaryButton type="button" onClick={() => addMaterial()}>
                + Material
              </PrimaryButton>
            </div>

            <Card className="overflow-hidden p-0">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[960px] text-left text-sm">
                  <thead className="sticky top-0 z-10 bg-black/[0.04] text-xs uppercase text-muted">
                    <tr>
                      <th className="px-4 py-2">Categoría</th>
                      <th className="px-4 py-2">Descripción</th>
                      <th className="px-4 py-2">Unidad</th>
                      <th className="px-4 py-2">Cant. est.</th>
                      <th className="px-4 py-2">Desp. %</th>
                      <th className="px-4 py-2">Cant. total</th>
                      <th className="px-4 py-2">Costo est.</th>
                      <th className="px-4 py-2">Proveedor</th>
                      <th className="px-4 py-2" aria-label="Acciones" />
                    </tr>
                  </thead>
                  <tbody>
                    {data.materiales.map((m) => (
                      <tr key={m.id} className="border-t border-black/5 odd:bg-black/[0.015]">
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input w-28 py-1.5 text-sm"
                            value={m.categoria ?? ''}
                            onChange={(e) => updateMaterial(m.id, { categoria: e.target.value || null })}
                            aria-label="Categoría"
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input min-w-[200px] py-1.5 text-sm"
                            value={m.descripcion}
                            onChange={(e) => updateMaterial(m.id, { descripcion: e.target.value })}
                            aria-label="Descripción"
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input w-20 py-1.5 text-sm"
                            value={m.unidad ?? ''}
                            onChange={(e) => updateMaterial(m.id, { unidad: e.target.value || null })}
                            aria-label="Unidad"
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input w-24 py-1.5 text-sm"
                            type="number"
                            min={0}
                            step="any"
                            value={m.cantidad_estimada ?? ''}
                            onChange={(e) => {
                              const v = e.target.value
                              updateMaterial(m.id, {
                                cantidad_estimada: v === '' ? null : Number(v),
                              })
                            }}
                            aria-label="Cantidad estimada"
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input w-20 py-1.5 text-sm"
                            type="number"
                            min={0}
                            max={100}
                            step="any"
                            value={m.desperdicio_porcentaje ?? ''}
                            onChange={(e) => {
                              const v = e.target.value
                              updateMaterial(m.id, {
                                desperdicio_porcentaje: v === '' ? null : Number(v),
                              })
                            }}
                            aria-label="Desperdicio porcentaje"
                          />
                        </td>
                        <td className="px-4 py-2 align-top text-sm tabular-nums text-ink">
                          {m.cantidad_total != null
                            ? m.cantidad_total.toLocaleString(undefined, {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 3,
                              })
                            : '—'}
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input w-28 py-1.5 text-sm"
                            type="number"
                            min={0}
                            step="any"
                            value={m.costo_estimado ?? ''}
                            onChange={(e) => {
                              const v = e.target.value
                              updateMaterial(m.id, {
                                costo_estimado: v === '' ? null : Number(v),
                              })
                            }}
                            aria-label="Costo estimado"
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input w-40 py-1.5 text-sm"
                            value={m.proveedor_sugerido ?? ''}
                            onChange={(e) =>
                              updateMaterial(m.id, { proveedor_sugerido: e.target.value || null })
                            }
                            aria-label="Proveedor sugerido"
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <button
                            type="button"
                            className="text-xs font-semibold text-primary underline-offset-2 hover:underline"
                            onClick={() => removeMaterial(m.id)}
                          >
                            Quitar
                          </button>
                        </td>
                      </tr>
                    ))}
                    {data.materiales.length === 0 ? (
                      <tr>
                        <td className="px-4 py-8 text-center text-sm text-muted" colSpan={9}>
                          No hay materiales. Usa «+ Material» para agregar una fila.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        ) : null}
      </Tabs>
    </>
  )
}
