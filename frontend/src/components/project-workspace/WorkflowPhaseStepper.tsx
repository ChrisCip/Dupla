import { WORKFLOW_PHASE_LABELS, WORKFLOW_PHASE_ORDER } from '../../constants/workflowPhases'

function phaseStepIndex(phase: string): number {
  if (phase === 'FILES_INGESTED') {
    const i = WORKFLOW_PHASE_ORDER.indexOf('AWAITING_FILES')
    return i >= 0 ? i : 0
  }
  const i = WORKFLOW_PHASE_ORDER.indexOf(phase as (typeof WORKFLOW_PHASE_ORDER)[number])
  return i >= 0 ? i : 0
}

type WorkflowPhaseStepperProps = {
  workflowPhase: string
  compact?: boolean
}

export function WorkflowPhaseStepper({ workflowPhase, compact }: WorkflowPhaseStepperProps) {
  const total = WORKFLOW_PHASE_ORDER.length
  const activeIdx = phaseStepIndex(workflowPhase)
  const label = WORKFLOW_PHASE_LABELS[workflowPhase] ?? workflowPhase

  if (compact) {
    return (
      <div
        data-tour="workspace-flujo-stepper"
        className="rounded-md border border-black/10 bg-black/[0.02] px-2 py-1.5 text-xs text-ink"
      >
        <span className="font-semibold tabular-nums">
          Fase {activeIdx + 1} / {total}
        </span>
        <span className="mt-0.5 block truncate text-[11px] font-medium leading-tight text-muted">{label}</span>
      </div>
    )
  }

  return (
    <div data-tour="workspace-flujo-stepper" className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">Progreso por fase</p>
      <div className="-mx-1 overflow-x-auto pb-1">
        <div className="flex min-w-max items-start px-1">
          {WORKFLOW_PHASE_ORDER.map((key, i) => {
            const isDone = i < activeIdx
            const isActive = i === activeIdx
            const stepLabel = WORKFLOW_PHASE_LABELS[key] ?? key
            return (
              <div key={key} className="flex items-start">
                {i > 0 ? (
                  <div
                    className={`mt-[13px] h-0.5 w-3 shrink-0 sm:w-5 ${isDone || isActive ? 'bg-primary/55' : 'bg-black/12'}`}
                    aria-hidden
                  />
                ) : null}
                <div className="flex w-[4.25rem] flex-col items-center gap-1 sm:w-[5.25rem]">
                  <span
                    className={`flex size-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold tabular-nums ${
                      isActive
                        ? 'bg-primary text-white ring-2 ring-primary/30'
                        : isDone
                          ? 'bg-primary/85 text-white'
                          : 'border border-black/15 bg-white text-muted'
                    }`}
                  >
                    {i + 1}
                  </span>
                  <span
                    className={`w-full text-center text-[9px] font-medium leading-tight sm:text-[10px] ${
                      isActive ? 'text-ink' : 'text-muted'
                    }`}
                    title={stepLabel}
                  >
                    {stepLabel}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
      <p className="text-sm font-medium text-ink">
        Actual: <span className="text-primary">{label}</span>
      </p>
    </div>
  )
}
