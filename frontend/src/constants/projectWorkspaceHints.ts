export type PhaseHint = {
  title: string
  body: string
  tabId: 'resumen' | 'flujo' | 'documentos' | 'revisiones' | 'historial'
  cta: string
}

export const PHASE_WORKSPACE_HINTS: Record<string, PhaseHint> = {
  BOOTSTRAPPING: {
    title: 'Arranque del proyecto',
    body: 'Completa el checklist de documentos y guárdalo. Luego avanza la fase cuando esté listo.',
    tabId: 'flujo',
    cta: 'Ir a Flujo',
  },
  AWAITING_FILES: {
    title: 'Subir archivos',
    body: 'Carga DWG/DXF o adjuntos en Documentos. Cuando estén cargados, avanza la fase.',
    tabId: 'documentos',
    cta: 'Ir a Documentos',
  },
  FILES_INGESTED: {
    title: 'Archivos listos',
    body: 'Revisa que los planos estén correctos y continúa hacia revisión de arquitectura.',
    tabId: 'flujo',
    cta: 'Ir a Flujo',
  },
  ARCHITECTURE_REVIEW: {
    title: 'Revisión de arquitectura',
    body: 'Registra la decisión (aprobado / rechazo / parcial) y las notas en Revisiones. Con aprobación, el siguiente paso formal es el pliego de condiciones antes del presupuesto.',
    tabId: 'revisiones',
    cta: 'Ir a Revisiones',
  },
  SPECIFICATIONS: {
    title: 'Pliego de condiciones',
    body: 'Aquí se documenta el pliego de condiciones: es el paso obligatorio antes del presupuesto. Redacta el resumen (mín. 10 caracteres) y guarda; luego podrás avanzar la fase a Presupuesto.',
    tabId: 'flujo',
    cta: 'Ir a Flujo — pliego',
  },
  BUDGETING_PIPELINE: {
    title: 'Pipeline de presupuesto',
    body: 'Con el pliego de condiciones cerrado, trabaja cotizaciones, volumetría y análisis; registra subcontratos si aplica.',
    tabId: 'flujo',
    cta: 'Ir a Flujo — presupuesto',
  },
  MANAGEMENT_APPROVAL: {
    title: 'Aprobación de gerencia',
    body: 'El presupuesto interno está listo: validación formal de gerencia antes de registrar la versión aprobada por el cliente.',
    tabId: 'flujo',
    cta: 'Ir a Flujo',
  },
  BUDGET_APPROVED: {
    title: 'Pliego y materiales',
    body: 'Arma secciones (tiradas / planos / fases) y la cubicación en Documentos. Exporta Excel/PDF cuando convenga.',
    tabId: 'documentos',
    cta: 'Ir a Documentos — pliegos',
  },
}
