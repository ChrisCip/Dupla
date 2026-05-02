import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { ProjectConfigModal } from '../components/ProjectConfigModal'
import { ProjectWorkspaceFlowAside } from '../components/project-workspace/ProjectWorkspaceFlowAside'
import { ProjectWorkspaceHeader } from '../components/project-workspace/ProjectWorkspaceHeader'
import { ProjectWorkspaceHub } from '../components/project-workspace/ProjectWorkspaceHub'
import { WorkspaceArchivosTab } from '../components/project-workspace/tabs/WorkspaceArchivosTab'
import { WorkspaceDetallesTab } from '../components/project-workspace/tabs/WorkspaceDetallesTab'
import { WorkspaceEntregaPlanosTab } from '../components/project-workspace/tabs/WorkspaceEntregaPlanosTab'
import { WorkspaceEspecificacionesTab } from '../components/project-workspace/tabs/WorkspaceEspecificacionesTab'
import { WorkspaceEventosTab } from '../components/project-workspace/tabs/WorkspaceEventosTab'
import { WorkspaceHallazgosTab } from '../components/project-workspace/tabs/WorkspaceHallazgosTab'
import { WorkspaceFlujoTab } from '../components/project-workspace/tabs/WorkspaceFlujoTab'
import { WorkspaceRevisionesTab } from '../components/project-workspace/tabs/WorkspaceRevisionesTab'
import { WorkspaceTabsLayout } from '../components/project-workspace/WorkspaceTabsLayout'
import {
  BUSINESS_PLIEGO_SECTION_KEYS,
  emptyBusinessPliegoSections,
  isBusinessPliegoReady,
  parseBusinessPliegoFromSpec,
  type BusinessPliegoSectionKey,
} from '../constants/businessPliego'
import { defaultBootstrapCriteria } from '../constants/defaultBootstrapCriteria'
import { TUTORIAL_PROJECT_UUID } from '../constants/tutorialProject'
import { loadAdminDirectoryUsers } from '../lib/adminUsersDirectoryCache'
import type { DirectoryUserRow } from '../lib/directoryUsers'
import { normalizeDirectoryUsers } from '../lib/directoryUsers'
import { projectWorkspaceSectionTabs, projectWorkspaceTabs } from '../constants/projectWorkspaceTabs'
import { NEXT_WORKFLOW_PHASE, WORKFLOW_PHASE_LABELS } from '../constants/workflowPhases'
import { budgetPipeline } from '../lib/budgetPipeline'
import { mergePliegoItemStates } from '../lib/pliegoFormState'
import { useAuthStore } from '../store/authStore'
import type { PlanDeliveryRow } from '../types/planDelivery'
import type { PliegoItemState } from '../types/pliegoForm'
import type { RevisionRow, SubcontractQuoteRow, TechnicalFindingRow } from '../types/projectWorkspace'
import type { BootstrapCriterion, Project } from '../types/project'
import type { WorkflowTemplateDetail } from '../types/workflowTemplate'

export function ProjectWorkspacePage() {
  const { projectUuid = '' } = useParams()
  const [searchParams] = useSearchParams()
  const token = useAuthStore((s) => s.token)
  const role = useAuthStore((s) => s.role)
  const [tab, setTab] = useState<string>('hub')
  const [project, setProject] = useState<Project | null>(null)
  const [flowTemplateDetail, setFlowTemplateDetail] = useState<WorkflowTemplateDetail | null>(null)
  const [projectError, setProjectError] = useState<string | null>(null)
  const [flowMsg, setFlowMsg] = useState<string | null>(null)
  const [flowBusy, setFlowBusy] = useState(false)
  const [bootstrapDraft, setBootstrapDraft] = useState<BootstrapCriterion[]>([])
  const [specSummary, setSpecSummary] = useState('')
  const [pliegoItemStates, setPliegoItemStates] = useState<Record<string, PliegoItemState>>(() =>
    mergePliegoItemStates(undefined),
  )
  const [specSaveBusy, setSpecSaveBusy] = useState(false)
  const [businessPliegoSections, setBusinessPliegoSections] = useState(() => emptyBusinessPliegoSections())
  const [pliegoMeta, setPliegoMeta] = useState<{ approved: boolean; generatedAt: string | null }>({
    approved: false,
    generatedAt: null,
  })
  const [pliegoGenerateBusy, setPliegoGenerateBusy] = useState(false)
  const [pliegoApproveBusy, setPliegoApproveBusy] = useState(false)
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
  const [memberRows, setMemberRows] = useState<DirectoryUserRow[]>([])
  const [adminUsers, setAdminUsers] = useState<DirectoryUserRow[]>([])
  const [membersBusy, setMembersBusy] = useState(false)
  const [membersMsg, setMembersMsg] = useState<string | null>(null)
  const [memberSelection, setMemberSelection] = useState<Set<string>>(new Set())
  const [planDeliveryRows, setPlanDeliveryRows] = useState<PlanDeliveryRow[]>([])
  const [planDeliveryMsg, setPlanDeliveryMsg] = useState<string | null>(null)
  const [findings, setFindings] = useState<TechnicalFindingRow[]>([])
  const [configOpen, setConfigOpen] = useState(false)

  const workspaceTabs = useMemo(() => projectWorkspaceTabs(), [])
  const sectionTabs = useMemo(() => projectWorkspaceSectionTabs(), [])

  useEffect(() => {
    if (!token || !project?.workflow_template_uuid) {
      setFlowTemplateDetail(null)
      return
    }
    let cancelled = false
    void (async () => {
      const res = await apiFetch(`/api/workflow-templates/${project.workflow_template_uuid}`, { token })
      if (!res.ok || cancelled) return
      setFlowTemplateDetail((await res.json()) as WorkflowTemplateDetail)
    })()
    return () => {
      cancelled = true
    }
  }, [token, project?.workflow_template_uuid])

  const templateStepProgress = useMemo(() => {
    if (!project || !flowTemplateDetail?.steps?.length) return null
    const ordered = [...flowTemplateDetail.steps].sort((a, b) => a.sort_index - b.sort_index)
    const idx = ordered.findIndex((s) => s.uuid === project.current_workflow_step_uuid)
    if (idx < 0) return null
    return { current: idx + 1, total: ordered.length }
  }, [project, flowTemplateDetail])

  const orderedTemplateSteps = useMemo(() => {
    if (!flowTemplateDetail?.steps?.length) return null
    return [...flowTemplateDetail.steps]
      .sort((a, b) => a.sort_index - b.sort_index)
      .map((s) => ({ uuid: s.uuid, title: s.title }))
  }, [flowTemplateDetail])

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
    const rawCrit = body.project_bootstrap_criteria ?? []
    const needsBootstrapFallback =
      body.workflow_phase === 'BOOTSTRAPPING' &&
      (!Array.isArray(rawCrit) || rawCrit.length === 0)
    setBootstrapDraft(needsBootstrapFallback ? defaultBootstrapCriteria() : rawCrit)
    const spec = body.specifications_document ?? {}
    setSpecSummary(typeof spec.summary === 'string' ? spec.summary : '')
    const ga = spec.ga_fo_01_arquitectura
    const rawPliegoStates =
      ga && typeof ga === 'object' && ga !== null && 'item_states' in ga
        ? (ga as { item_states?: Record<string, unknown> }).item_states
        : undefined
    setPliegoItemStates(mergePliegoItemStates(rawPliegoStates))
    const bpParsed = parseBusinessPliegoFromSpec(body.specifications_document)
    setBusinessPliegoSections(bpParsed.sections)
    setPliegoMeta({ approved: bpParsed.approved, generatedAt: bpParsed.generatedAt })
    setBpDraft(budgetPipeline(body.workflow_meta ?? {}))
    setClientVersion(
      typeof budgetPipeline(body.workflow_meta ?? {}).client_approved_version_label === 'string'
        ? (budgetPipeline(body.workflow_meta ?? {}).client_approved_version_label as string)
        : '',
    )
  }, [projectUuid, token])

  useEffect(() => {
    if (projectUuid === TUTORIAL_PROJECT_UUID) {
      setTab('detalles')
    }
  }, [projectUuid])

  useEffect(() => {
    const raw = searchParams.get('tab')?.trim()
    const aliases: Record<string, string> = {
      especificaciones: 'pliego',
      pliegos: 'hub',
      materiales: 'hub',
      presupuesto: 'flujo',
    }
    const candidate = raw ? aliases[raw] ?? raw : null
    if (candidate && workspaceTabs.some((t) => t.id === candidate)) {
      setTab(candidate)
      return
    }
    if (raw) {
      setTab('hub')
      return
    }
    if (projectUuid !== TUTORIAL_PROJECT_UUID) {
      setTab('hub')
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

  const loadFindings = useCallback(async () => {
    if (!token || !projectUuid) return
    const res = await apiFetch(`/api/projects/${projectUuid}/technical-findings`, { token })
    if (!res.ok) return
    setFindings((await res.json()) as TechnicalFindingRow[])
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
    if (tab === 'archivos' || tab === 'revisiones' || tab === 'flujo') {
      void loadAuxLists()
    }
  }, [tab, projectUuid, token, loadAuxLists])

  useEffect(() => {
    if (!projectUuid || !token) return
    if (tab === 'hallazgos') void loadFindings()
  }, [tab, projectUuid, token, loadFindings])

  useEffect(() => {
    if (tab !== 'entregaPlanos' || !projectUuid || !token) return
    void loadPlanDelivery()
  }, [tab, projectUuid, token, loadPlanDelivery])

  useEffect(() => {
    const ids = new Set(workspaceTabs.map((t) => t.id))
    if (!ids.has(tab)) {
      setTab('hub')
    }
  }, [workspaceTabs, tab])

  useEffect(() => {
    if (!token || !projectUuid || role !== 'GERENCIA' || !project) return
    let cancelled = false
    void (async () => {
      const [m, adminRows] = await Promise.all([
        apiFetch(`/api/projects/${projectUuid}/members`, { token }),
        loadAdminDirectoryUsers(token),
      ])
      if (cancelled) return
      if (m.ok) setMemberRows(normalizeDirectoryUsers(await m.json()))
      if (adminRows !== null) setAdminUsers(adminRows)
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
    if (next === 'BUDGETING_PIPELINE') {
      const spec = project.specifications_document
      const specObj = spec && typeof spec === 'object' ? (spec as Record<string, unknown>) : undefined
      const hasStructured = Boolean(
        specObj?.business_pliego && typeof specObj.business_pliego === 'object',
      )
      const parsed = parseBusinessPliegoFromSpec(specObj)
      if (hasStructured) {
        if (!isBusinessPliegoReady(parsed.sections, parsed.approved)) {
          setFlowMsg(
            'Completa las nueve secciones del pliego (mín. 10 caracteres cada una) y obtén aprobación de Gerencia o Arquitectura.',
          )
          return
        }
      } else if (specSummary.trim().length < 10) {
        setFlowMsg('Completa el pliego: resumen mínimo 10 caracteres o genera el pliego estructurado.')
        return
      }
    }
    if (next === 'BUDGET_APPROVED') {
      if (!bpDraft.control_review_done) {
        setFlowMsg(
          'Completa la revisión de Control en la pestaña Flujo (pipeline de presupuesto) antes de avanzar a presupuesto aprobado.',
        )
        return
      }
      if (!clientVersion.trim()) {
        setFlowMsg(
          'Indica la etiqueta de versión aprobada por el cliente en Flujo — pipeline de presupuesto antes de avanzar.',
        )
        return
      }
    }
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
      const prev = project.specifications_document ?? {}
      const prevBp =
        prev && typeof prev === 'object' && 'business_pliego' in prev
          ? (prev as Record<string, unknown>).business_pliego
          : null
      const pbd = prevBp && typeof prevBp === 'object' ? (prevBp as Record<string, unknown>) : null
      const hasSectionText = BUSINESS_PLIEGO_SECTION_KEYS.some(
        (k) => (businessPliegoSections[k]?.trim().length ?? 0) > 0,
      )
      const includeBusinessPliego =
        pbd != null || pliegoMeta.generatedAt != null || hasSectionText
      const doc: Record<string, unknown> = {
        ...prev,
        summary: specSummary,
        ga_fo_01_arquitectura: {
          schema_version: 1 as const,
          item_states: pliegoItemStates,
        },
      }
      if (includeBusinessPliego) {
        doc.business_pliego = {
          schema_version: 1,
          sections: businessPliegoSections,
          generated_at: typeof pbd?.generated_at === 'string' ? pbd.generated_at : null,
          approved: Boolean(pbd?.approved),
          approved_at: typeof pbd?.approved_at === 'string' ? pbd.approved_at : null,
          approved_by_user_uuid:
            typeof pbd?.approved_by_user_uuid === 'string' ? pbd.approved_by_user_uuid : null,
        }
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
      const p = j as Project
      setProject(p)
      const parsed = parseBusinessPliegoFromSpec(p.specifications_document)
      setBusinessPliegoSections(parsed.sections)
      setPliegoMeta({ approved: parsed.approved, generatedAt: parsed.generatedAt })
    } finally {
      setSpecSaveBusy(false)
    }
  }

  async function generatePliego(force: boolean) {
    if (!token) return
    setFlowMsg(null)
    setPliegoGenerateBusy(true)
    try {
      const res = await apiFetch(`/api/projects/${projectUuid}/specifications/generate`, {
        method: 'POST',
        token,
        body: JSON.stringify({ force }),
      })
      const j = await res.json().catch(() => ({}))
      if (!res.ok) {
        setFlowMsg((j as { detail?: string }).detail ?? 'No se pudo generar el borrador')
        return
      }
      const p = j as Project
      setProject(p)
      const parsed = parseBusinessPliegoFromSpec(p.specifications_document)
      setBusinessPliegoSections(parsed.sections)
      setPliegoMeta({ approved: parsed.approved, generatedAt: parsed.generatedAt })
    } finally {
      setPliegoGenerateBusy(false)
    }
  }

  async function approvePliego() {
    if (!token) return
    setFlowMsg(null)
    setPliegoApproveBusy(true)
    try {
      const res = await apiFetch(`/api/projects/${projectUuid}/specifications/approve`, {
        method: 'POST',
        token,
        body: JSON.stringify({}),
      })
      const j = await res.json().catch(() => ({}))
      if (!res.ok) {
        setFlowMsg((j as { detail?: string }).detail ?? 'No se pudo aprobar el pliego')
        return
      }
      const p = j as Project
      setProject(p)
      const parsed = parseBusinessPliegoFromSpec(p.specifications_document)
      setBusinessPliegoSections(parsed.sections)
      setPliegoMeta({ approved: parsed.approved, generatedAt: parsed.generatedAt })
    } finally {
      setPliegoApproveBusy(false)
    }
  }

  function onBusinessSectionChange(key: BusinessPliegoSectionKey, value: string) {
    setBusinessPliegoSections((s) => ({ ...s, [key]: value }))
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
  const phaseLabel = project
    ? project.current_step_title?.trim()
      ? project.current_step_title
      : (WORKFLOW_PHASE_LABELS[project.workflow_phase] ?? project.workflow_phase)
    : ''
  const nextPhase = project ? NEXT_WORKFLOW_PHASE[project.workflow_phase] : undefined

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden">
      <ProjectWorkspaceHeader
        displayTitle={displayTitle}
        phaseLabel={phaseLabel}
        projectUuid={projectUuid}
        token={token}
        status="idle"
        lastSavedAt={null}
        lastError={null}
        onOpenConfig={() => setConfigOpen(true)}
      />

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <WorkspaceTabsLayout tabs={workspaceTabs} activeId={tab} onSelect={setTab} labelledBy="workspace-heading">
          {tab === 'hub' ? (
            <div className="flex min-h-0 flex-1 flex-col gap-3 px-3 py-4 sm:px-5 sm:py-5 md:flex-row md:items-stretch">
              <ProjectWorkspaceHub sectionTabs={sectionTabs} onOpenSection={(id) => setTab(id)} />
              <ProjectWorkspaceFlowAside
                projectUuid={projectUuid}
                workflowPhase={project?.workflow_phase ?? ''}
                phaseLabel={phaseLabel}
                templateStepProgress={templateStepProgress}
                nextPhase={nextPhase}
                flowBusy={flowBusy}
                flowMsg={flowMsg}
                role={role}
                onAdvancePhase={() => void advancePhase()}
                onOpenChat={() => void openProjectChat()}
              />
            </div>
          ) : null}

          {tab === 'detalles' ? (
            <WorkspaceDetallesTab
              project={project}
              projectError={projectError}
              phaseLabel={phaseLabel}
              token={token}
              onOpenChat={() => void openProjectChat()}
            />
          ) : null}

          {tab === 'flujo' ? (
            <WorkspaceFlujoTab
              project={project}
              projectUuid={projectUuid}
              token={token}
              phaseLabel={phaseLabel}
              templateStepProgress={templateStepProgress}
              orderedTemplateSteps={orderedTemplateSteps}
              flowMsg={flowMsg}
              flowBusy={flowBusy}
              bootstrapDraft={bootstrapDraft}
              setBootstrapDraft={setBootstrapDraft}
              nextPhase={nextPhase}
              role={role}
              onSaveBootstrap={() => void saveBootstrap()}
              onAdvancePhase={() => void advancePhase()}
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

          {tab === 'hallazgos' ? (
            <WorkspaceHallazgosTab
              projectUuid={projectUuid}
              token={token}
              findings={findings}
              onRefresh={() => loadFindings()}
            />
          ) : null}

          {tab === 'pliego' ? (
            <WorkspaceEspecificacionesTab
              projectUuid={projectUuid}
              token={token}
              role={role}
              specSummary={specSummary}
              setSpecSummary={setSpecSummary}
              pliegoItemStates={pliegoItemStates}
              setPliegoItemStates={setPliegoItemStates}
              onPersist={async () => {
                await saveSpecifications()
              }}
              specSaveBusy={specSaveBusy}
              flowMsg={flowMsg}
              businessSections={businessPliegoSections}
              onBusinessSectionChange={onBusinessSectionChange}
              onGeneratePliego={async (f) => {
                await generatePliego(f)
              }}
              onApprovePliego={async () => {
                await approvePliego()
              }}
              pliegoGenerateBusy={pliegoGenerateBusy}
              pliegoApproveBusy={pliegoApproveBusy}
              pliegoApproved={pliegoMeta.approved}
              pliegoGeneratedAt={pliegoMeta.generatedAt}
            />
          ) : null}

          {tab === 'eventos' ? <WorkspaceEventosTab token={token} projectUuid={projectUuid} /> : null}
        </WorkspaceTabsLayout>
      </div>

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
