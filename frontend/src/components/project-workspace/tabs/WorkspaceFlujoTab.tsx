import { Card } from '../../Card'
import { PrimaryButton } from '../../PrimaryButton'
import { WORKFLOW_PHASE_LABELS } from '../../../constants/workflowPhases'
import type { BootstrapCriterion, Project } from '../../../types/project'

type WorkspaceFlujoTabProps = {
  project: Project | null
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

export function WorkspaceFlujoTab({
  project,
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
  return (
    <Card className="space-y-4 p-6">
      <h2 className="text-lg font-semibold text-ink">Flujo de trabajo</h2>
      {project ? (
        <>
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
