import { Card } from '../Card'
import {
  effectivePrevWorkflowPhase,
  NEXT_WORKFLOW_PHASE,
  WORKFLOW_PHASE_LABELS,
  WORKFLOW_PHASE_ORDER,
} from '../../constants/workflowPhases'
import { formatProjectUpdatedAt, PROJECT_BOARD_PHASE_ICONS } from '../../constants/projectsPage'
import { projectKindLabel } from '../../constants/projectKind'
import type { Project } from '../../types/project'

type ProjectsBoardViewProps = {
  loadingList: boolean
  projects: Project[]
  filteredProjects: Project[]
  projectSearch: string
  boardMsg: string | null
  onDropOnPhaseColumn: (e: React.DragEvent, phaseKey: string) => void
  onDragOverBoard: (e: React.DragEvent) => void
  onDragStartProject: (e: React.DragEvent, projectUuid: string) => void
  onDragEndBoard: () => void
  onOpenCard: (projectUuid: string) => void
}

export function ProjectsBoardView({
  loadingList,
  projects,
  filteredProjects,
  projectSearch,
  boardMsg,
  onDropOnPhaseColumn,
  onDragOverBoard,
  onDragStartProject,
  onDragEndBoard,
  onOpenCard,
}: ProjectsBoardViewProps) {
  return (
    <Card
      data-tour="projects-board"
      className="flex min-h-0 flex-1 flex-col overflow-hidden p-0"
    >
      {boardMsg ? (
        <div className="flex shrink-0 border-b border-black/10 bg-white px-4 py-3">
          <p className="text-sm text-primary">{boardMsg}</p>
        </div>
      ) : null}
      {loadingList ? (
        <p className="shrink-0 px-4 py-6 text-sm text-muted">Cargando tablero…</p>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden p-1.5 pb-2">
          {projectSearch.trim() && filteredProjects.length === 0 && projects.length > 0 ? (
            <p className="shrink-0 px-2 pb-2 text-sm text-muted">
              Ningún proyecto coincide con «{projectSearch.trim()}». Prueba otro término o borra la búsqueda.
            </p>
          ) : null}
          <div className="min-h-0 flex-1 overflow-x-auto overflow-y-hidden">
            <div className="flex h-full w-max min-w-full items-stretch gap-1.5">
              {WORKFLOW_PHASE_ORDER.map((phaseKey) => {
                const label = WORKFLOW_PHASE_LABELS[phaseKey] ?? phaseKey
                const inColumn = filteredProjects.filter((p) => p.workflow_phase === phaseKey)
                const PhaseIcon = PROJECT_BOARD_PHASE_ICONS[phaseKey]
                return (
                  <div
                    key={phaseKey}
                    className="flex h-full min-h-0 w-[10rem] shrink-0 flex-col rounded-lg border border-black/10 bg-black/[0.02] shadow-[var(--shadow-card)] sm:w-[11rem]"
                    onDragOver={onDragOverBoard}
                    onDrop={(e) => onDropOnPhaseColumn(e, phaseKey)}
                  >
                    <div
                      className="flex min-h-[5.5rem] shrink-0 flex-col items-center justify-center gap-1.5 border-b border-white/25 bg-primary px-1.5 py-2.5 text-center text-white shadow-[inset_0_-1px_0_rgba(0,0,0,0.08)] sm:min-h-24"
                      title={label}
                    >
                      <PhaseIcon className="h-4 w-4 shrink-0 text-white" strokeWidth={2} aria-hidden />
                      <span className="w-full text-[10px] font-semibold uppercase leading-snug tracking-wide sm:text-xs">
                        {label}
                      </span>
                    </div>
                    <div className="min-h-0 flex-1 space-y-1 overflow-y-auto p-1">
                      {inColumn.map((p) => {
                        const hasNext = NEXT_WORKFLOW_PHASE[p.workflow_phase] !== undefined
                        const hasPrev =
                          effectivePrevWorkflowPhase(p.project_kind, p.workflow_phase) !== undefined
                        const canMovePhase = hasNext || hasPrev
                        return (
                          <div
                            key={p.uuid}
                            role="button"
                            tabIndex={0}
                            draggable={canMovePhase}
                            className={`group relative cursor-pointer overflow-hidden rounded-md border border-black/10 bg-white text-left shadow-sm ring-1 ring-black/[0.04] transition-all duration-200 hover:-translate-y-px hover:border-black/20 hover:shadow-md hover:ring-black/10 ${
                              canMovePhase ? '' : 'opacity-[0.92]'
                            }`}
                            onClick={() => onOpenCard(p.uuid)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault()
                                onOpenCard(p.uuid)
                              }
                            }}
                            onDragStart={(e) => onDragStartProject(e, p.uuid)}
                            onDragEnd={onDragEndBoard}
                          >
                            <div
                              className={`absolute inset-y-1 left-0 w-0.5 rounded-full ${canMovePhase ? 'bg-primary' : 'bg-black/20'}`}
                              aria-hidden
                            />
                            <div className="relative pl-2.5 pr-2 pb-2 pt-1.5">
                              <p className="mb-0.5 text-[10px] font-semibold uppercase leading-tight tracking-wide text-muted sm:text-xs">
                                {projectKindLabel(p.project_kind)}
                              </p>
                              <h3 className="line-clamp-2 pr-0.5 text-xs font-semibold leading-snug tracking-tight text-ink sm:text-sm">
                                {p.name}
                              </h3>
                              <div className="mt-1.5 space-y-1">
                                <div className="flex items-start gap-1">
                                  <span className="du-meta w-9 shrink-0 text-[10px] sm:text-xs">Cliente</span>
                                  <span className="min-w-0 flex-1 text-xs leading-snug text-ink sm:text-sm">
                                    {p.client_name?.trim() ? (
                                      <span className="line-clamp-2">{p.client_name}</span>
                                    ) : (
                                      <span className="text-muted">—</span>
                                    )}
                                  </span>
                                </div>
                                <div className="flex items-start gap-1 border-t border-black/[0.06] pt-1">
                                  <span className="du-meta w-9 shrink-0 text-[10px] sm:text-xs">Act.</span>
                                  <time
                                    className="min-w-0 flex-1 text-[10px] tabular-nums leading-snug text-ink sm:text-xs"
                                    dateTime={p.updated_at}
                                  >
                                    {formatProjectUpdatedAt(p.updated_at)}
                                  </time>
                                </div>
                              </div>
                              <div className="mt-1.5 flex items-start justify-between gap-1 border-t border-black/[0.05] pt-1">
                                {!canMovePhase ? (
                                  <span className="rounded bg-black/[0.05] px-1 py-0.5 text-[10px] font-semibold uppercase leading-tight tracking-wide text-muted sm:text-xs">
                                    Fin flujo
                                  </span>
                                ) : (
                                  <span className="text-[10px] font-medium uppercase leading-tight tracking-wide text-muted sm:text-xs">
                                    {hasPrev ? '←' : ''}
                                    {hasPrev && hasNext ? ' ' : ''}
                                    {hasNext ? '→' : ''}
                                  </span>
                                )}
                                <span className="text-[10px] font-medium leading-tight text-muted opacity-0 transition-opacity duration-200 group-hover:opacity-100 sm:text-xs">
                                  Abrir →
                                </span>
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}
