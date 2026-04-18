import { Link } from 'react-router-dom'

import { Card } from '../Card'
import { PrimaryButton } from '../PrimaryButton'
import { TaskboardView } from '../TaskboardView'
import { WORKFLOW_PHASE_LABELS } from '../../constants/workflowPhases'

type ProjectWorkspaceEmbeddedViewProps = {
  projectUuid: string
  phaseLabel: string
  nextPhase: string | undefined
  flowBusy: boolean
  flowMsg: string | null
  role: string | null
  onAdvancePhase: () => void
  onOpenChat: () => void
  onOpenWorkspace: () => void
}

export function ProjectWorkspaceEmbeddedView({
  projectUuid,
  phaseLabel,
  nextPhase,
  flowBusy,
  flowMsg,
  role,
  onAdvancePhase,
  onOpenChat,
  onOpenWorkspace,
}: ProjectWorkspaceEmbeddedViewProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden lg:flex-row lg:items-stretch">
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <p className="du-meta shrink-0 text-xs">
          Tareas del proyecto · arrastra entre columnas;
        </p>
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-black/10 bg-black/2">
          {projectUuid ? (
            <TaskboardView
              projectUuid={projectUuid}
              variant="embedded"
              maxVisibleColumns={4}
              hideEmbeddedHeader
            />
          ) : null}
        </div>
      </div>
      <aside className="flex w-full shrink-0 flex-col gap-3 overflow-y-auto lg:w-80">
        <Card className="p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted">Estado del flujo</h2>
          <p className="mt-2 text-sm font-medium text-ink">{phaseLabel || '—'}</p>
          {nextPhase ? (
            <PrimaryButton
              type="button"
              className="mt-3 w-full"
              disabled={flowBusy}
              onClick={onAdvancePhase}
            >
              {flowBusy
                ? 'Procesando…'
                : `Avanzar a: ${WORKFLOW_PHASE_LABELS[nextPhase] ?? nextPhase}`}
            </PrimaryButton>
          ) : (
            <p className="du-meta mt-2 text-sm">Última fase alcanzada.</p>
          )}
          {nextPhase === 'BUDGET_APPROVED' && role !== 'GERENCIA' ? (
            <p className="mt-2 text-xs text-primary">
              Solo Gerencia puede cerrar la aprobación final del presupuesto.
            </p>
          ) : null}
          {flowMsg ? <p className="mt-2 text-sm text-primary">{flowMsg}</p> : null}
        </Card>
        <Card className="p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted">Acciones rápidas</h2>
          <div className="mt-3 flex flex-col gap-2">
            <Link
              className="du-pill-action text-center"
              to={`/app/tasks?project_uuid=${encodeURIComponent(projectUuid)}`}
            >
              Tablero completo
            </Link>
            <button type="button" className="du-pill-action" onClick={onOpenChat}>
              Chat del proyecto
            </button>
            <button
              type="button"
              className="du-pill-action border-primary/40 bg-primary/[0.06] font-semibold text-primary"
              onClick={onOpenWorkspace}
            >
              Ver workspace
            </button>
          </div>
        </Card>
      </aside>
    </div>
  )
}
