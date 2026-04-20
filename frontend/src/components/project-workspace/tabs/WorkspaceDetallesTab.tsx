import { Link } from 'react-router-dom'

import { projectKindLabel } from '../../../constants/projectKind'
import { Card } from '../../Card'
import type { Project } from '../../../types/project'

type WorkspaceDetallesTabProps = {
  project: Project | null
  projectError: string | null
  phaseLabel: string
  onOpenChat: () => void
}

export function WorkspaceDetallesTab({
  project,
  projectError,
  phaseLabel,
  onOpenChat,
}: WorkspaceDetallesTabProps) {
  return (
    <Card className="p-6">
      <h2 className="text-lg font-semibold text-ink">Detalles del proyecto</h2>
      {projectError ? <p className="mt-3 text-sm text-primary">{projectError}</p> : null}
      {!project && !projectError ? <p className="mt-3 text-sm text-muted">Cargando…</p> : null}
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
              <dt className="du-meta">Tipo de proyecto</dt>
              <dd className="mt-1 text-sm text-ink">{projectKindLabel(project.project_kind)}</dd>
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
              data-tour="workspace-project-tasks-link"
              className="du-pill-action"
              to={`/app/tasks?project_uuid=${encodeURIComponent(project.uuid)}`}
            >
              Tablero del proyecto
            </Link>
            <button
              data-tour="workspace-project-chat-btn"
              type="button"
              className="du-pill-action"
              onClick={onOpenChat}
            >
              Chat del proyecto
            </button>
          </div>
        </>
      ) : null}
    </Card>
  )
}
