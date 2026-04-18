/** Orden lineal del flujo (para indicadores visuales). */
export const WORKFLOW_PHASE_ORDER = [
  'BOOTSTRAPPING',
  'AWAITING_FILES',
  'FILES_INGESTED',
  'ARCHITECTURE_REVIEW',
  'SPECIFICATIONS',
  'BUDGETING_PIPELINE',
  'MANAGEMENT_APPROVAL',
  'BUDGET_APPROVED',
] as const

export const WORKFLOW_PHASE_LABELS: Record<string, string> = {
  BOOTSTRAPPING: 'Criterios de arranque',
  AWAITING_FILES: 'Esperando archivos CAD',
  FILES_INGESTED: 'Archivos ingresados',
  ARCHITECTURE_REVIEW: 'Revisión de arquitectura',
  SPECIFICATIONS: 'Pliego de condiciones',
  BUDGETING_PIPELINE: 'Presupuesto (cotización / volumetría / costo)',
  MANAGEMENT_APPROVAL: 'Aprobación de gerencia',
  BUDGET_APPROVED: 'Presupuesto aprobado por cliente',
}

/** Siguiente fase en el flujo lineal (ISO). */
export const NEXT_WORKFLOW_PHASE: Record<string, string | undefined> = {
  BOOTSTRAPPING: 'AWAITING_FILES',
  AWAITING_FILES: 'FILES_INGESTED',
  FILES_INGESTED: 'ARCHITECTURE_REVIEW',
  ARCHITECTURE_REVIEW: 'SPECIFICATIONS',
  SPECIFICATIONS: 'BUDGETING_PIPELINE',
  BUDGETING_PIPELINE: 'MANAGEMENT_APPROVAL',
  MANAGEMENT_APPROVAL: 'BUDGET_APPROVED',
  BUDGET_APPROVED: undefined,
}

/** Fase anterior inmediata (retroceso de un paso). */
export const PREV_WORKFLOW_PHASE: Record<string, string | undefined> = {
  AWAITING_FILES: 'BOOTSTRAPPING',
  FILES_INGESTED: 'AWAITING_FILES',
  ARCHITECTURE_REVIEW: 'FILES_INGESTED',
  SPECIFICATIONS: 'ARCHITECTURE_REVIEW',
  BUDGETING_PIPELINE: 'SPECIFICATIONS',
  MANAGEMENT_APPROVAL: 'BUDGETING_PIPELINE',
  BUDGET_APPROVED: 'MANAGEMENT_APPROVAL',
}
