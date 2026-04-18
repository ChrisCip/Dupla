import { WORKFLOW_PHASE_ORDER } from './workflowPhases'

/**
 * Pestañas del workspace de proyecto (`ProjectWorkspacePage`).
 * `minPhaseIndex` es el índice mínimo en WORKFLOW_PHASE_ORDER para mostrar la pestaña.
 */
const TAB_DEFS: { id: string; label: string; minPhaseIndex: number }[] = [
  { id: 'detalles', label: 'Detalles', minPhaseIndex: 0 },
  { id: 'flujo', label: 'Flujo', minPhaseIndex: 0 },
  { id: 'archivos', label: 'Archivos', minPhaseIndex: 1 },
  { id: 'entregaPlanos', label: 'Entrega planos', minPhaseIndex: 2 },
  { id: 'revisiones', label: 'Revisiones', minPhaseIndex: 2 },
  { id: 'especificaciones', label: 'Especificaciones', minPhaseIndex: 3 },
  { id: 'presupuesto', label: 'Presupuesto', minPhaseIndex: 4 },
  { id: 'eventos', label: 'Eventos', minPhaseIndex: 0 },
  { id: 'pliegos', label: 'Pliegos', minPhaseIndex: 6 },
  { id: 'materiales', label: 'Materiales', minPhaseIndex: 6 },
]

/** Pestañas visibles según la fase ISO actual del proyecto. */
export function projectWorkspaceTabs(workflowPhase: string): { id: string; label: string }[] {
  const idx = WORKFLOW_PHASE_ORDER.indexOf(workflowPhase as (typeof WORKFLOW_PHASE_ORDER)[number])
  const active = idx >= 0 ? idx : 0
  return TAB_DEFS.filter((t) => t.minPhaseIndex <= active).map(({ id, label }) => ({ id, label }))
}
