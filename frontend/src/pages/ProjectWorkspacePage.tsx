import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { Card } from '../components/Card'
import { PrimaryButton } from '../components/PrimaryButton'
import { StatusBadge } from '../components/StatusBadge'
import { Tabs } from '../components/Tabs'
import { PHASE_WORKSPACE_HINTS } from '../constants/projectWorkspaceHints'
import {
  NEXT_WORKFLOW_PHASE,
  WORKFLOW_PHASE_LABELS,
  WORKFLOW_PHASE_ORDER,
} from '../constants/workflowPhases'
import { useAuthStore } from '../store/authStore'
import { useWorkspaceStore } from '../store/workspaceStore'
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

const WORKSPACE_TABS = [
  { id: 'detalles', label: 'Detalles' },
  { id: 'flujo', label: 'Flujo' },
  { id: 'archivos', label: 'Archivos' },
  { id: 'revisiones', label: 'Revisiones' },
  { id: 'especificaciones', label: 'Especificaciones' },
  { id: 'presupuesto', label: 'Presupuesto' },
  { id: 'eventos', label: 'Eventos' },
  { id: 'pliegos', label: 'Pliegos' },
  { id: 'materiales', label: 'Materiales' },
] as const

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
    const doc = { ...project.specifications_document, summary: specSummary }
    const res = await apiFetch(`/api/projects/${projectUuid}/specifications`, {
      method: 'PUT',
      token,
      body: JSON.stringify({ document: doc }),
    })
    const j = await res.json().catch(() => ({}))
    if (!res.ok) {
      setFlowMsg((j as { detail?: string }).detail ?? 'Error al guardar especificaciones')
      return
    }
    setProject(j as Project)
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
  const phaseOrderList = WORKFLOW_PHASE_ORDER as readonly string[]
  const activePhaseIndex = project ? phaseOrderList.indexOf(project.workflow_phase) : -1
  const workspaceHint = project
    ? (PHASE_WORKSPACE_HINTS[project.workflow_phase] ?? {
        title: 'Workspace',
        body: 'Usa las pestañas para archivos, flujo, pliegos y materiales.',
        tabId: 'detalles' as const,
        cta: 'Ir a Detalles',
      })
    : null

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
          <p className="mt-1 du-meta">Workspace del proyecto</p>
        </div>
        <div className="flex w-full flex-col gap-4 sm:w-auto sm:items-end">
          <StatusBadge status={status} lastSavedAt={lastSavedAt} errorMessage={lastError} />
          <p className="w-full text-left text-xs text-muted sm:text-right">
            Las exportaciones pueden tardar unos segundos; el botón muestra «Generando…» mientras descarga.
          </p>
          <div className="flex w-full flex-wrap gap-2 sm:justify-end">
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
        </div>
      </div>

      {project && workspaceHint ? (
        <div className="mb-6 space-y-4">
          <div
            className="flex gap-1 overflow-x-auto border border-black/10 bg-white px-2 py-2 text-[11px] shadow-[var(--shadow-card)] sm:text-xs"
            aria-label="Progreso del flujo por fases"
          >
            {WORKFLOW_PHASE_ORDER.map((phaseKey, i) => {
              const label = WORKFLOW_PHASE_LABELS[phaseKey] ?? phaseKey
              const isCurrent = project.workflow_phase === phaseKey
              const isPast = activePhaseIndex >= 0 && i < activePhaseIndex
              return (
                <div
                  key={phaseKey}
                  className={`shrink-0 rounded-md px-2 py-1.5 font-medium transition-colors duration-150 ${
                    isCurrent
                      ? 'bg-primary/12 text-ink ring-1 ring-primary/30'
                      : isPast
                        ? 'bg-black/[0.05] text-muted'
                        : 'text-muted'
                  }`}
                  title={label}
                >
                  {label}
                </div>
              )
            })}
          </div>
          <div className="du-callout flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <div className="text-sm font-semibold text-ink">Siguiente paso sugerido</div>
              <p className="mt-1 text-sm leading-relaxed text-muted">
                <span className="font-medium text-ink">{workspaceHint.title}.</span> {workspaceHint.body}
              </p>
            </div>
            <PrimaryButton
              type="button"
              className="shrink-0 sm:min-w-[10rem]"
              disabled={tab === workspaceHint.tabId}
              onClick={() => setTab(workspaceHint.tabId)}
            >
              {tab === workspaceHint.tabId ? 'En esta pestaña' : workspaceHint.cta}
            </PrimaryButton>
          </div>
        </div>
      ) : !project && !projectError ? (
        <div className="du-callout mb-6 border-black/15 bg-black/[0.03] text-muted">
          Cargando datos del proyecto… Cuando estén listos verás la franja de fases y una sugerencia de siguiente paso.
        </div>
      ) : null}

      <Tabs tabs={[...WORKSPACE_TABS]} value={tab} onChange={setTab} labelledBy="workspace-heading">
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
                {nextPhase === 'BUDGET_APPROVED' && role !== 'MASTER' ? (
                  <p className="text-sm text-primary">
                    Solo un usuario MASTER puede marcar la aprobación final del presupuesto.
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

        {tab === 'revisiones' ? (
          <Card className="space-y-4 p-6">
            <h2 className="text-lg font-semibold text-ink">Revisiones de arquitectura</h2>
            {flowMsg ? <p className="text-sm text-primary">{flowMsg}</p> : null}
            {project?.workflow_phase === 'ARCHITECTURE_REVIEW' ? (
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
            ) : null}
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
          <Card className="space-y-4 p-6">
            <h2 className="text-lg font-semibold text-ink">Especificaciones</h2>
            <p className="text-sm text-muted">
              Resumen del pliego (mínimo 10 caracteres) para avanzar a la fase de presupuesto.
            </p>
            {flowMsg ? <p className="text-sm text-primary">{flowMsg}</p> : null}
            <textarea
              className="du-input min-h-[160px] w-full text-sm"
              value={specSummary}
              onChange={(e) => setSpecSummary(e.target.value)}
            />
            <PrimaryButton type="button" onClick={() => void saveSpecifications()}>
              Guardar
            </PrimaryButton>
          </Card>
        ) : null}

        {tab === 'presupuesto' ? (
          <div className="space-y-6">
            <Card className="space-y-4 p-6">
              <h2 className="text-lg font-semibold text-ink">Pipeline de presupuesto</h2>
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
