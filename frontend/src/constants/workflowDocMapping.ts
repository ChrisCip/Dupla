/**
 * Equivalencia corta «documento de negocio ↔ fase Dupla» (ver docs/modules/flujo-doc-vs-dupla.md).
 */
export const WORKFLOW_DOC_PHASE_HINTS: Record<string, string> = {
  BOOTSTRAPPING: 'Doc: obra creada; criterios de arranque y checklist inicial.',
  AWAITING_FILES: 'Doc: documentación cargada; pendiente completar archivos CAD/PDF.',
  FILES_INGESTED: 'Doc (legado): archivos ingresados; equivale a «esperando archivos» en flujo nuevo.',
  ARCHITECTURE_REVIEW: 'Doc: en revisión de arquitectura.',
  SPECIFICATIONS: 'Doc: pliego de condiciones / especificaciones.',
  BUDGETING_PIPELINE: 'Doc: presupuesto — cotizaciones, volumetría, costo e hitos del pipeline.',
  MANAGEMENT_APPROVAL: 'Doc: revisión Control / gerencia antes del cierre económico.',
  BUDGET_APPROVED: 'Doc: versión aprobada por el cliente.',
  COMPLETE: 'Doc: obra cerrada en flujo.',
}

export const WORKFLOW_DOC_MAPPING_SUMMARY = [
  'Creado → BOOTSTRAPPING / creación.',
  'Documentación cargada → AWAITING_FILES.',
  'En clasificación / análisis → checklist + archivos (sin sub-estados dedicados).',
  'Informes → informe documental exportable (PDF).',
  'Revisión arquitectura → ARCHITECTURE_REVIEW.',
  'Hacia presupuesto → SPECIFICATIONS → BUDGETING_PIPELINE.',
  'Control / gerencia → MANAGEMENT_APPROVAL y flags del pipeline (revisión Control).',
  'Aprobado cliente → BUDGET_APPROVED → COMPLETE.',
] as const
