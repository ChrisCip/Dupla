/** Orden lineal del flujo (para indicadores visuales). */
export const WORKFLOW_PHASE_ORDER = [
  'BOOTSTRAPPING',
  'AWAITING_FILES',
  'ARCHITECTURE_REVIEW',
  'SPECIFICATIONS',
  'BUDGETING_PIPELINE',
  'MANAGEMENT_APPROVAL',
  'BUDGET_APPROVED',
  'COMPLETE',
] as const

export const WORKFLOW_PHASE_LABELS: Record<string, string> = {
  BOOTSTRAPPING: 'Criterios de arranque',
  AWAITING_FILES: 'Esperando archivos CAD',
  /** Legado / tareas creadas antes del cambio de flujo */
  FILES_INGESTED: 'Archivos ingresados',
  ARCHITECTURE_REVIEW: 'Revisión de arquitectura',
  SPECIFICATIONS: 'Pliego de condiciones',
  BUDGETING_PIPELINE: 'Presupuesto (cotización / volumetría / costo)',
  MANAGEMENT_APPROVAL: 'Aprobación de gerencia',
  BUDGET_APPROVED: 'Presupuesto aprobado por cliente',
  COMPLETE: 'Completo',
}

/** Siguiente fase en el flujo lineal (ISO). */
export const NEXT_WORKFLOW_PHASE: Record<string, string | undefined> = {
  BOOTSTRAPPING: 'AWAITING_FILES',
  AWAITING_FILES: 'ARCHITECTURE_REVIEW',
  ARCHITECTURE_REVIEW: 'SPECIFICATIONS',
  SPECIFICATIONS: 'BUDGETING_PIPELINE',
  BUDGETING_PIPELINE: 'MANAGEMENT_APPROVAL',
  MANAGEMENT_APPROVAL: 'BUDGET_APPROVED',
  BUDGET_APPROVED: 'COMPLETE',
  COMPLETE: undefined,
}

/** Fase anterior inmediata (retroceso de un paso). */
export const PREV_WORKFLOW_PHASE: Record<string, string | undefined> = {
  AWAITING_FILES: 'BOOTSTRAPPING',
  ARCHITECTURE_REVIEW: 'AWAITING_FILES',
  SPECIFICATIONS: 'ARCHITECTURE_REVIEW',
  BUDGETING_PIPELINE: 'SPECIFICATIONS',
  MANAGEMENT_APPROVAL: 'BUDGETING_PIPELINE',
  BUDGET_APPROVED: 'MANAGEMENT_APPROVAL',
  COMPLETE: 'BUDGET_APPROVED',
}
