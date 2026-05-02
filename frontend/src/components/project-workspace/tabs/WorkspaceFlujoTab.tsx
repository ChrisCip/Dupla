import { useEffect, useMemo, useState } from 'react'

import { apiFetch } from '../../../api/client'
import { WORKFLOW_DOC_PHASE_HINTS } from '../../../constants/workflowDocMapping'
import { WORKFLOW_PHASE_LABELS } from '../../../constants/workflowPhases'
import { downloadBlob, filenameFromContentDisposition } from '../../../lib/download'
import type { SubcontractQuoteRow } from '../../../types/projectWorkspace'
import type { BootstrapCriterion, Project } from '../../../types/project'
import { Card } from '../../Card'
import { PrimaryButton } from '../../PrimaryButton'
import { WorkflowPhaseStepper, type TemplateStepProgress } from '../WorkflowPhaseStepper'

type WorkspaceFlujoTabProps = {
  project: Project | null
  projectUuid: string
  token: string | null
  phaseLabel: string
  templateStepProgress?: TemplateStepProgress | null
  orderedTemplateSteps?: { uuid: string; title: string }[] | null
  flowMsg: string | null
  flowBusy: boolean
  bootstrapDraft: BootstrapCriterion[]
  setBootstrapDraft: React.Dispatch<React.SetStateAction<BootstrapCriterion[]>>
  nextPhase: string | undefined
  role: string | null
  onSaveBootstrap: () => void
  onAdvancePhase: () => void
  bpDraft: Record<string, unknown>
  setBpDraft: React.Dispatch<React.SetStateAction<Record<string, unknown>>>
  clientVersion: string
  setClientVersion: React.Dispatch<React.SetStateAction<string>>
  onSaveBudgetPipeline: () => void
  newQuoteTitle: string
  setNewQuoteTitle: React.Dispatch<React.SetStateAction<string>>
  activeQuote: string
  setActiveQuote: React.Dispatch<React.SetStateAction<string>>
  lineItem: string
  setLineItem: React.Dispatch<React.SetStateAction<string>>
  linePrice: string
  setLinePrice: React.Dispatch<React.SetStateAction<string>>
  quotes: SubcontractQuoteRow[]
  onLoadAuxLists: () => Promise<void>
}

function bootstrapRequiredPercent(criteria: BootstrapCriterion[]): { pct: number | null; label: string } {
  const required = criteria.filter((c) => c.required)
  if (required.length === 0) return { pct: null, label: 'Sin ítems obligatorios en el checklist.' }
  const done = required.filter((c) => c.done).length
  return {
    pct: Math.round((done / required.length) * 100),
    label: `${done} de ${required.length} ítems obligatorios cumplidos`,
  }
}

export function WorkspaceFlujoTab({
  project,
  projectUuid,
  token,
  phaseLabel,
  templateStepProgress,
  orderedTemplateSteps,
  flowMsg,
  flowBusy,
  bootstrapDraft,
  setBootstrapDraft,
  nextPhase,
  role,
  onSaveBootstrap,
  onAdvancePhase,
  bpDraft,
  setBpDraft,
  clientVersion,
  setClientVersion,
  onSaveBudgetPipeline,
  newQuoteTitle,
  setNewQuoteTitle,
  activeQuote,
  setActiveQuote,
  lineItem,
  setLineItem,
  linePrice,
  setLinePrice,
  quotes,
  onLoadAuxLists,
}: WorkspaceFlujoTabProps) {
  const [fileTotal, setFileTotal] = useState<number | null>(null)
  const [docBusy, setDocBusy] = useState(false)

  const bootstrapStats = useMemo(() => bootstrapRequiredPercent(bootstrapDraft), [bootstrapDraft])
  const docHint = project ? WORKFLOW_DOC_PHASE_HINTS[project.workflow_phase] ?? null : null
  const showBudgetPanel =
    !!project &&
    ['BUDGETING_PIPELINE', 'MANAGEMENT_APPROVAL', 'BUDGET_APPROVED', 'COMPLETE'].includes(project.workflow_phase)
  const canMarkControl = role === 'CONTROL' || role === 'GERENCIA'
  const awaitingBudgetApproval = project?.workflow_phase === 'MANAGEMENT_APPROVAL'
  const missingControlGate = awaitingBudgetApproval && !bpDraft.control_review_done
  const missingClientVersion = awaitingBudgetApproval && !clientVersion.trim()

  useEffect(() => {
    if (!token || !projectUuid) return
    let cancelled = false
    void (async () => {
      const res = await apiFetch(`/api/projects/${projectUuid}/files?limit=1&offset=0`, { token })
      if (!res.ok || cancelled) return
      const body = (await res.json()) as { total: number }
      if (!cancelled) setFileTotal(body.total)
    })()
    return () => {
      cancelled = true
    }
  }, [token, projectUuid])

  async function downloadDocumentaryReport() {
    if (!token) return
    setDocBusy(true)
    try {
      const res = await apiFetch(`/api/projects/${projectUuid}/exports/documentary-report.pdf`, { token })
      if (!res.ok) return
      const blob = await res.blob()
      downloadBlob(blob, filenameFromContentDisposition(res, `informe-documental-${projectUuid}.pdf`))
    } finally {
      setDocBusy(false)
    }
  }

  if (!project) {
    return (
      <Card className="space-y-4 p-6">
        <h2 className="text-lg font-semibold text-ink">Flujo de trabajo</h2>
        <p className="text-sm text-muted">Cargando…</p>
      </Card>
    )
  }

  return (
    <div className="flex w-full flex-col gap-4">
      <Card className="space-y-4 p-6">
        <h2 className="text-lg font-semibold text-ink">Flujo de trabajo</h2>
        <>
          <WorkflowPhaseStepper
            workflowPhase={project.workflow_phase}
            templateStepProgress={templateStepProgress}
            stepTitle={phaseLabel}
            templateSteps={orderedTemplateSteps}
            currentWorkflowStepUuid={project.current_workflow_step_uuid}
          />
          {docHint ? (
            <p className="rounded-md border border-black/10 bg-black/[0.02] px-3 py-2 text-xs text-muted">{docHint}</p>
          ) : null}

          <div className="rounded-md border border-black/10 bg-black/[0.02] p-4">
            <p className="text-sm font-medium text-ink">Documentación y archivos</p>
            <p className="mt-1 text-sm text-muted">
              Archivos en el proyecto:{' '}
              <strong className="text-ink">{fileTotal != null ? fileTotal : '…'}</strong>
            </p>
            <button
              type="button"
              disabled={docBusy || !token}
              className="du-pill-action mt-3 border-primary/30 bg-primary/[0.06] text-sm font-semibold text-primary"
              onClick={() => void downloadDocumentaryReport()}
            >
              {docBusy ? 'Generando…' : 'Descargar informe documental (PDF)'}
            </button>
          </div>

          <p className="rounded-md border border-black/10 bg-black/[0.02] px-3 py-2 text-sm text-muted">
            Fase actual: <span className="font-semibold text-ink">{phaseLabel}</span>. Avanza solo cuando el trabajo de
            esta etapa esté hecho; si el botón falla, el mensaje de arriba indica el motivo.
          </p>
          {flowMsg ? <p className="text-sm text-primary">{flowMsg}</p> : null}
          {nextPhase ? (
            <PrimaryButton type="button" disabled={flowBusy} onClick={onAdvancePhase}>
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

          {showBudgetPanel ? (
            <div className="space-y-6 border-t border-black/10 pt-6">
              <Card className="space-y-4 p-6">
                <h3 className="text-base font-semibold text-ink">Pipeline de presupuesto</h3>
                <p className="text-sm text-muted">
                  Hitos y revisión de Control se registran aquí antes de avanzar a «Presupuesto aprobado por cliente».
                </p>
                {awaitingBudgetApproval && (missingControlGate || missingClientVersion) ? (
                  <div className="rounded-md border border-primary/25 bg-primary/[0.06] px-3 py-2 text-sm text-ink">
                    Para avanzar: marcá la revisión de Control y la etiqueta de versión aprobada por el cliente (guardá
                    abajo).{' '}
                    {missingControlGate ? <span className="font-medium text-primary">Falta revisión de Control.</span> : null}{' '}
                    {missingClientVersion ? (
                      <span className="font-medium text-primary">Falta versión del cliente.</span>
                    ) : null}
                  </div>
                ) : null}
                <div className="space-y-3 border-t border-black/10 pt-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">Hitos del pipeline</p>
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
                </div>
                <div className="space-y-2 border-l-2 border-primary/35 pl-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">Control</p>
                  <label className={`flex items-center gap-2 text-sm ${!canMarkControl ? 'opacity-60' : ''}`}>
                    <input
                      type="checkbox"
                      disabled={!canMarkControl}
                      checked={!!bpDraft.control_review_done}
                      onChange={(e) => setBpDraft((d) => ({ ...d, control_review_done: e.target.checked }))}
                    />
                    Revisión de Control completada
                    {!canMarkControl ? (
                      <span className="text-xs text-muted">(solo Control o Gerencia)</span>
                    ) : null}
                  </label>
                </div>
                <div className="space-y-2 border-t border-black/10 pt-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">Cliente</p>
                  <label className="block text-sm text-muted">
                    Etiqueta de versión aprobada por el cliente
                    <input
                      className="du-input mt-1"
                      value={clientVersion}
                      onChange={(e) => setClientVersion(e.target.value)}
                      placeholder="ej. v2"
                    />
                  </label>
                </div>
                <PrimaryButton type="button" onClick={onSaveBudgetPipeline}>
                  Guardar estado del pipeline
                </PrimaryButton>
              </Card>
              <Card className="space-y-4 p-6">
                <h3 className="text-base font-semibold text-ink">Cotizaciones</h3>
                <div className="flex flex-wrap gap-2">
                  <input
                    className="du-input min-w-[160px] flex-1"
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
                        await onLoadAuxLists()
                      }
                    }}
                  >
                    Nueva cotización
                  </PrimaryButton>
                </div>
                <label className="block text-sm text-muted">
                  Cotización activa para líneas
                  <select className="du-input mt-1" value={activeQuote} onChange={(e) => setActiveQuote(e.target.value)}>
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
                    className="du-input min-w-[120px] flex-1"
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
                      const res = await apiFetch(`/api/projects/${projectUuid}/subcontracts/${activeQuote}/lines`, {
                        method: 'POST',
                        token,
                        body: JSON.stringify({
                          item_label: lineItem.trim(),
                          price: Number(linePrice),
                          currency: 'MXN',
                        }),
                      })
                      if (res.ok) {
                        setLineItem('')
                        setLinePrice('')
                        await onLoadAuxLists()
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
        </>
      </Card>

      <Card className="space-y-4 p-6">
        <h2 className="text-lg font-semibold text-ink">Checklist de documentos requeridos</h2>
        <p className="text-sm text-muted">
          Marcá los ítems obligatorios antes de seguir desde la etapa «Arranque». La aplicación solo permite avanzar
          cuando esos requisitos estén cumplidos; el siguiente paso es «Esperando archivos».
        </p>
        <p className="text-sm text-muted">
          {bootstrapStats.pct != null ? (
            <>
              Progreso (obligatorios): <strong className="text-ink">{bootstrapStats.pct}%</strong> —{' '}
              {bootstrapStats.label}
            </>
          ) : (
            bootstrapStats.label
          )}
        </p>
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
        <PrimaryButton type="button" onClick={onSaveBootstrap}>
          Guardar checklist
        </PrimaryButton>
      </Card>
    </div>
  )
}
