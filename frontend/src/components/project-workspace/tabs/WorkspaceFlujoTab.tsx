import { useEffect, useMemo, useState } from 'react'

import { apiFetch } from '../../../api/client'
import { WORKFLOW_DOC_MAPPING_SUMMARY, WORKFLOW_DOC_PHASE_HINTS } from '../../../constants/workflowDocMapping'
import { WORKFLOW_PHASE_LABELS } from '../../../constants/workflowPhases'
import { downloadBlob, filenameFromContentDisposition } from '../../../lib/download'
import type { BootstrapCriterion, Project } from '../../../types/project'
import { Card } from '../../Card'
import { PrimaryButton } from '../../PrimaryButton'
import { WorkflowPhaseStepper } from '../WorkflowPhaseStepper'

type WorkspaceFlujoTabProps = {
  project: Project | null
  projectUuid: string
  token: string | null
  phaseLabel: string
  flowMsg: string | null
  flowBusy: boolean
  bootstrapDraft: BootstrapCriterion[]
  setBootstrapDraft: React.Dispatch<React.SetStateAction<BootstrapCriterion[]>>
  nextPhase: string | undefined
  role: string | null
  onSaveBootstrap: () => void
  onAdvancePhase: () => void
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
  flowMsg,
  flowBusy,
  bootstrapDraft,
  setBootstrapDraft,
  nextPhase,
  role,
  onSaveBootstrap,
  onAdvancePhase,
}: WorkspaceFlujoTabProps) {
  const [fileTotal, setFileTotal] = useState<number | null>(null)
  const [docBusy, setDocBusy] = useState(false)

  const bootstrapStats = useMemo(() => bootstrapRequiredPercent(bootstrapDraft), [bootstrapDraft])
  const docHint = project ? WORKFLOW_DOC_PHASE_HINTS[project.workflow_phase] ?? null : null

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

  return (
    <Card className="space-y-4 p-6">
      <h2 className="text-lg font-semibold text-ink">Flujo de trabajo</h2>
      {project ? (
        <>
          <WorkflowPhaseStepper workflowPhase={project.workflow_phase} />
          {docHint ? (
            <p className="rounded-md border border-black/10 bg-black/[0.02] px-3 py-2 text-xs text-muted">{docHint}</p>
          ) : null}
          <details className="rounded-md border border-black/10 bg-white px-3 py-2 text-sm">
            <summary className="cursor-pointer font-medium text-ink">Equivalencia con el documento de negocio</summary>
            <ul className="mt-2 list-inside list-disc space-y-1 text-muted">
              {WORKFLOW_DOC_MAPPING_SUMMARY.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </details>

          <div className="rounded-md border border-black/10 bg-black/[0.02] p-4">
            <p className="text-sm font-medium text-ink">Documentación y archivos</p>
            <p className="mt-1 text-sm text-muted">
              {bootstrapStats.pct != null ? (
                <>
                  Checklist (ítems obligatorios): <strong className="text-ink">{bootstrapStats.pct}%</strong> —{' '}
                  {bootstrapStats.label}
                </>
              ) : (
                bootstrapStats.label
              )}
            </p>
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
              <PrimaryButton type="button" onClick={onSaveBootstrap}>
                Guardar checklist
              </PrimaryButton>
            </div>
          ) : null}
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
        </>
      ) : (
        <p className="text-sm text-muted">Cargando…</p>
      )}
    </Card>
  )
}
