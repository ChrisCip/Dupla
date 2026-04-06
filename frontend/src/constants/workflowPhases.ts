/** Orden lineal del flujo (para indicadores visuales). */
export const WORKFLOW_PHASE_ORDER = [
  'BOOTSTRAPPING',
  'AWAITING_FILES',
  'FILES_INGESTED',
  'ARCHITECTURE_REVIEW',
  'SPECIFICATIONS',
  'BUDGETING_PIPELINE',
  'BUDGET_APPROVED',
] as const

export const WORKFLOW_PHASE_LABELS: Record<string, string> = {
  BOOTSTRAPPING: 'Criterios de arranque',
  AWAITING_FILES: 'Esperando archivos CAD',
  FILES_INGESTED: 'Archivos ingresados',
  ARCHITECTURE_REVIEW: 'Revisión de arquitectura',
  SPECIFICATIONS: 'Pliego de condiciones',
  BUDGETING_PIPELINE: 'Presupuesto (cotización / volumetría / costo)',
  BUDGET_APPROVED: 'Presupuesto aprobado por cliente',
}

/** Siguiente fase en el flujo lineal (ISO). */
export const NEXT_WORKFLOW_PHASE: Record<string, string | undefined> = {
  BOOTSTRAPPING: 'AWAITING_FILES',
  AWAITING_FILES: 'FILES_INGESTED',
  FILES_INGESTED: 'ARCHITECTURE_REVIEW',
  ARCHITECTURE_REVIEW: 'SPECIFICATIONS',
  SPECIFICATIONS: 'BUDGETING_PIPELINE',
  BUDGETING_PIPELINE: 'BUDGET_APPROVED',
  BUDGET_APPROVED: undefined,
}
