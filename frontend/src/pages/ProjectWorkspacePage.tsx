import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { ProjectConfigModal } from '../components/ProjectConfigModal'
import { ProjectWorkspaceEmbeddedView } from '../components/project-workspace/ProjectWorkspaceEmbeddedView'
import { ProjectWorkspaceHeader } from '../components/project-workspace/ProjectWorkspaceHeader'
import { WorkspaceArchivosTab } from '../components/project-workspace/tabs/WorkspaceArchivosTab'
import { WorkspaceDetallesTab } from '../components/project-workspace/tabs/WorkspaceDetallesTab'
import { WorkspaceEntregaPlanosTab } from '../components/project-workspace/tabs/WorkspaceEntregaPlanosTab'
import { WorkspaceEspecificacionesTab } from '../components/project-workspace/tabs/WorkspaceEspecificacionesTab'
import { WorkspaceEventosTab } from '../components/project-workspace/tabs/WorkspaceEventosTab'
import { WorkspaceFlujoTab } from '../components/project-workspace/tabs/WorkspaceFlujoTab'
import { WorkspaceMaterialesTab } from '../components/project-workspace/tabs/WorkspaceMaterialesTab'
import { WorkspacePliegosTab } from '../components/project-workspace/tabs/WorkspacePliegosTab'
import { WorkspacePresupuestoTab } from '../components/project-workspace/tabs/WorkspacePresupuestoTab'
import { WorkspaceRevisionesTab } from '../components/project-workspace/tabs/WorkspaceRevisionesTab'
import { WorkspaceTabsLayout } from '../components/project-workspace/WorkspaceTabsLayout'
import { TUTORIAL_PROJECT_UUID } from '../constants/tutorialProject'
import { projectWorkspaceTabs } from '../constants/projectWorkspaceTabs'
import { NEXT_WORKFLOW_PHASE, WORKFLOW_PHASE_LABELS } from '../constants/workflowPhases'
import { budgetPipeline } from '../lib/budgetPipeline'
import { mergePliegoItemStates } from '../lib/pliegoFormState'
import { useAuthStore } from '../store/authStore'
import { useWorkspaceStore } from '../store/workspaceStore'
import type { PlanDeliveryRow } from '../types/planDelivery'
import type { PliegoItemState } from '../types/pliegoForm'
import type { RevisionRow, SubcontractQuoteRow } from '../types/projectWorkspace'
import type { BootstrapCriterion, Project } from '../types/project'

export function ProjectWorkspacePage() {
  const { projectUuid = '' } = useParams()
  const [searchParams] = useSearchParams()
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
  const [revisions, setRevisions] = useState<RevisionRow[]>([])
  const [quotes, setQuotes] = useState<SubcontractQuoteRow[]>([])
  const [revDecision, setRevDecision] = useState('APPROVED')
  const [revNotes, setRevNotes] = useState('')
  const [bpDraft, setBpDraft] = useState<Record<string, unknown>>({})
  const [clientVersion, setClientVersion] = useState('')
  const [newQuoteTitle, setNewQuoteTitle] = useState('')
  const [lineItem, setLineItem] = useState('')
  const [linePrice, setLinePrice] = useState('')
  const [activeQuote, setActiveQuote] = useState('')
  const [memberRows, setMemberRows] = useState<
    { uuid: string; email: string; first_name: string; last_name: string }[]
  >([])
  const [adminUsers, setAdminUsers] = useState<
    { uuid: string; email: string; first_name: string; last_name: string }[]
  >([])
  const [membersBusy, setMembersBusy] = useState(false)
  const [membersMsg, setMembersMsg] = useState<string | null>(null)
  const [memberSelection, setMemberSelection] = useState<Set<string>>(new Set())
  const [planDeliveryRows, setPlanDeliveryRows] = useState<PlanDeliveryRow[]>([])
  const [planDeliveryMsg, setPlanDeliveryMsg] = useState<string | null>(null)
  const [configOpen, setConfigOpen] = useState(false)
  const [workspaceOpen, setWorkspaceOpen] = useState(false)

  const workspaceTabs = useMemo(() => projectWorkspaceTabs(), [])

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
    if (projectUuid === TUTORIAL_PROJECT_UUID) {
      setWorkspaceOpen(true)
    }
  }, [projectUuid])

  useEffect(() => {
    const tabParam = searchParams.get('tab')
    if (tabParam && workspaceTabs.some((t) => t.id === tabParam)) {
      setTab(tabParam)
    } else {
      setTab('detalles')
    }
  }, [projectUuid, searchParams, workspaceTabs])

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
    const [fr, fq] = await Promise.all([
      apiFetch(`/api/projects/${projectUuid}/architecture-revisions`, { token }),
      apiFetch(`/api/projects/${projectUuid}/subcontracts`, { token }),
    ])
    if (fr.ok) setRevisions((await fr.json()) as RevisionRow[])
    if (fq.ok) setQuotes((await fq.json()) as SubcontractQuoteRow[])
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

  async function addPlanDeliveryRow(payload?: { description?: string; request_date?: string | null }) {
    if (!token || !projectUuid) return false
    setPlanDeliveryMsg(null)
    const body: Record<string, unknown> = {
      description: payload?.description?.trim() ?? '',
      status: 'SOLICITADO',
    }
    if (payload?.request_date) body.request_date = payload.request_date
    const res = await apiFetch(`/api/projects/${projectUuid}/plan-delivery-requests`, {
      method: 'POST',
      token,
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      setPlanDeliveryMsg('No se pudo crear la solicitud')
      return false
    }
    const row = (await res.json()) as PlanDeliveryRow
    setPlanDeliveryRows((prev) => [...prev, row])
    return true
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
    if (tab === 'archivos' || tab === 'revisiones' || tab === 'presupuesto') {
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
      if (m.ok)
        setMemberRows(
          (await m.json()) as {
            uuid: string
            email: string
            first_name: string
            last_name: string
          }[],
        )
      if (u.ok)
        setAdminUsers(
          (await u.json()) as {
            uuid: string
            email: string
            first_name: string
            last_name: string
          }[],
        )
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
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden">
      <ProjectWorkspaceHeader
        displayTitle={displayTitle}
        phaseLabel={phaseLabel}
        projectUuid={projectUuid}
        token={token}
        status={status}
        lastSavedAt={lastSavedAt}
        lastError={lastError}
        onOpenConfig={() => setConfigOpen(true)}
      />

      {!workspaceOpen ? (
        <ProjectWorkspaceEmbeddedView
          projectUuid={projectUuid}
          phaseLabel={phaseLabel}
          nextPhase={nextPhase}
          flowBusy={flowBusy}
          flowMsg={flowMsg}
          role={role}
          onAdvancePhase={() => void advancePhase()}
          onOpenChat={() => void openProjectChat()}
          onOpenWorkspace={() => {
            setWorkspaceOpen(true)
            setTab('detalles')
          }}
        />
      ) : (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-black/10 pb-2">
            <button
              type="button"
              className="rounded-md px-3 py-2 text-sm font-medium text-primary hover:bg-primary/[0.08]"
              onClick={() => setWorkspaceOpen(false)}
            >
              ← Volver al tablero
            </button>
          </div>
          <WorkspaceTabsLayout
            tabs={workspaceTabs}
            activeId={tab}
            onSelect={setTab}
            labelledBy="workspace-heading"
          >
        {tab === 'detalles' ? (
                <WorkspaceDetallesTab
                  project={project}
                  projectError={projectError}
                  phaseLabel={phaseLabel}
                  onOpenChat={() => void openProjectChat()}
                />
        ) : null}

        {tab === 'flujo' ? (
                <WorkspaceFlujoTab
                  project={project}
                  phaseLabel={phaseLabel}
                  flowMsg={flowMsg}
                  flowBusy={flowBusy}
                  bootstrapDraft={bootstrapDraft}
                  setBootstrapDraft={setBootstrapDraft}
                  nextPhase={nextPhase}
                  role={role}
                  onSaveBootstrap={() => void saveBootstrap()}
                  onAdvancePhase={() => void advancePhase()}
                />
        ) : null}

        {tab === 'archivos' ? (
                <WorkspaceArchivosTab projectUuid={projectUuid} token={token} flowMsg={flowMsg} />
        ) : null}

        {tab === 'entregaPlanos' ? (
                <WorkspaceEntregaPlanosTab
                  projectUuid={projectUuid}
                  token={token}
                  planDeliveryRows={planDeliveryRows}
                  planDeliveryMsg={planDeliveryMsg}
                  setPlanDeliveryRows={setPlanDeliveryRows}
                  onAddRow={(payload) => addPlanDeliveryRow(payload)}
                  onPatchRow={(rowUuid, patch) => void patchPlanDeliveryRow(rowUuid, patch)}
                  onDeleteRow={(rowUuid) => void deletePlanDeliveryRow(rowUuid)}
                />
        ) : null}

        {tab === 'revisiones' ? (
                <WorkspaceRevisionesTab
                  flowMsg={flowMsg}
                  revDecision={revDecision}
                  setRevDecision={setRevDecision}
                  revNotes={revNotes}
                  setRevNotes={setRevNotes}
                  revisions={revisions}
                  onSubmitRevision={() => void submitRevision()}
                />
        ) : null}

        {tab === 'especificaciones' ? (
                <WorkspaceEspecificacionesTab
              projectUuid={projectUuid}
              token={token}
              specSummary={specSummary}
                  setSpecSummary={setSpecSummary}
                  pliegoItemStates={pliegoItemStates}
                  setPliegoItemStates={setPliegoItemStates}
                  onPersist={() => saveSpecifications()}
                  specSaveBusy={specSaveBusy}
              flowMsg={flowMsg}
            />
        ) : null}

        {tab === 'presupuesto' ? (
                <WorkspacePresupuestoTab
                  projectUuid={projectUuid}
                  token={token}
                  flowMsg={flowMsg}
                  bpDraft={bpDraft}
                  setBpDraft={setBpDraft}
                  clientVersion={clientVersion}
                  setClientVersion={setClientVersion}
                  onSaveBudgetPipeline={() => void saveBudgetPipeline()}
                  newQuoteTitle={newQuoteTitle}
                  setNewQuoteTitle={setNewQuoteTitle}
                  activeQuote={activeQuote}
                  setActiveQuote={setActiveQuote}
                  lineItem={lineItem}
                  setLineItem={setLineItem}
                  linePrice={linePrice}
                  setLinePrice={setLinePrice}
                  quotes={quotes}
                  onLoadAuxLists={loadAuxLists}
                />
        ) : null}

              {tab === 'eventos' ? <WorkspaceEventosTab token={token} projectUuid={projectUuid} /> : null}

        {tab === 'pliegos' ? (
                <WorkspacePliegosTab
                  kind={kind}
                  setKind={setKind}
                  title={title}
                  setTitle={setTitle}
                  data={data}
                  addGroup={addGroup}
                  addItem={addItem}
                  updateItem={updateItem}
                />
              ) : null}

              {tab === 'materiales' ? (
                <WorkspaceMaterialesTab
                  data={data}
                  addMaterial={addMaterial}
                  updateMaterial={updateMaterial}
                  removeMaterial={removeMaterial}
                />
                        ) : null}
          </WorkspaceTabsLayout>
        </div>
      )}

      <ProjectConfigModal
        open={configOpen}
        onClose={() => setConfigOpen(false)}
        projectUuid={projectUuid}
        token={token}
        role={role}
        project={project}
        projectError={projectError}
        onProjectSaved={(p) => {
          setProject(p)
          void loadAuxLists()
        }}
        adminUsers={adminUsers}
        memberRows={memberRows}
        memberSelection={memberSelection}
        setMemberSelection={setMemberSelection}
        membersBusy={membersBusy}
        setMembersBusy={setMembersBusy}
        membersMsg={membersMsg}
        setMembersMsg={setMembersMsg}
        setMemberRows={setMemberRows}
      />
              </div>
  )
}
