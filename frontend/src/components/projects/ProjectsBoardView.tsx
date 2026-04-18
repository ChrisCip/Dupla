import { Card } from '../Card'
import { PrimaryButton } from '../PrimaryButton'
import {
  NEXT_WORKFLOW_PHASE,
  PREV_WORKFLOW_PHASE,
  WORKFLOW_PHASE_LABELS,
  WORKFLOW_PHASE_ORDER,
} from '../../constants/workflowPhases'
import { formatProjectUpdatedAt, PROJECT_BOARD_PHASE_ICONS } from '../../constants/projectsPage'
import type { Project } from '../../types/project'

type ProjectsBoardViewProps = {
  loadingList: boolean
  projects: Project[]
  filteredProjects: Project[]
  projectSearch: string
  boardMsg: string | null
  role: string | null
  onOpenCreate: () => void
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
  role,
  onOpenCreate,
  onDropOnPhaseColumn,
  onDragOverBoard,
  onDragStartProject,
  onDragEndBoard,
  onOpenCard,
}: ProjectsBoardViewProps) {
  return (
    <Card className="flex min-h-0 flex-1 flex-col overflow-hidden p-0">
      {role === 'GERENCIA' || boardMsg ? (
        <div
          className={`flex shrink-0 flex-wrap items-center gap-3 border-b border-black/10 bg-white px-4 py-3 ${
            boardMsg && role === 'GERENCIA'
              ? 'justify-between'
              : boardMsg
                ? 'justify-start'
                : 'justify-end'
          }`}
        >
          {boardMsg ? (
            <p className={`text-sm text-primary ${role === 'GERENCIA' ? 'min-w-0 flex-1' : ''}`}>{boardMsg}</p>
          ) : null}
          {role === 'GERENCIA' ? (
            <PrimaryButton type="button" className="shrink-0" onClick={onOpenCreate}>
              Nuevo proyecto
            </PrimaryButton>
          ) : null}
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
                      className="flex h-12 shrink-0 flex-col items-center justify-center gap-0.5 border-b border-white/25 bg-primary px-1 py-1 text-center text-white shadow-[inset_0_-1px_0_rgba(0,0,0,0.08)]"
                      title={label}
                    >
                      <PhaseIcon className="h-3 w-3 shrink-0 text-white" strokeWidth={2} aria-hidden />
                      <span className="line-clamp-2 w-full text-[7px] font-semibold uppercase leading-tight tracking-wide sm:text-[8px]">
                        {label}
                      </span>
                    </div>
                    <div className="min-h-0 flex-1 space-y-1 overflow-y-auto p-1">
                      {inColumn.map((p) => {
                        const hasNext = NEXT_WORKFLOW_PHASE[p.workflow_phase] !== undefined
                        const hasPrev = PREV_WORKFLOW_PHASE[p.workflow_phase] !== undefined
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
                            <div className="relative pl-2 pr-1.5 pb-1.5 pt-1">
                              <h3 className="line-clamp-2 pr-0.5 text-[10px] font-semibold leading-snug tracking-tight text-ink sm:text-[11px]">
                                {p.name}
                              </h3>
                              <div className="mt-1 space-y-0.5">
                                <div className="flex items-start gap-0.5">
                                  <span className="du-meta w-8 shrink-0 text-[8px]">Cliente</span>
                                  <span className="min-w-0 flex-1 text-[9px] leading-snug text-ink sm:text-[10px]">
                                    {p.client_name?.trim() ? (
                                      <span className="line-clamp-2">{p.client_name}</span>
                                    ) : (
                                      <span className="text-muted">—</span>
                                    )}
                                  </span>
                                </div>
                                <div className="flex items-start gap-0.5 border-t border-black/[0.06] pt-0.5">
                                  <span className="du-meta w-8 shrink-0 text-[8px]">Act.</span>
                                  <time
                                    className="min-w-0 flex-1 text-[8px] tabular-nums leading-snug text-ink sm:text-[9px]"
                                    dateTime={p.updated_at}
                                  >
                                    {formatProjectUpdatedAt(p.updated_at)}
                                  </time>
                                </div>
                              </div>
                              <div className="mt-1 flex items-start justify-between gap-0.5 border-t border-black/[0.05] pt-1">
                                {!canMovePhase ? (
                                  <span className="rounded bg-black/[0.05] px-0.5 py-0.5 text-[7px] font-semibold uppercase leading-tight tracking-wide text-muted">
                                    Fin flujo
                                  </span>
                                ) : (
                                  <span className="text-[7px] font-medium uppercase leading-tight tracking-wide text-muted sm:text-[8px]">
                                    {hasPrev ? '←' : ''}
                                    {hasPrev && hasNext ? ' ' : ''}
                                    {hasNext ? '→' : ''}
                                  </span>
                                )}
                                <span className="text-[8px] font-medium leading-tight text-muted opacity-0 transition-opacity duration-200 group-hover:opacity-100">
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
