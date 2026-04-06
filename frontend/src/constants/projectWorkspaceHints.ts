export type PhaseHint = {
  title: string
  body: string
  tabId:
    | 'detalles'
    | 'flujo'
    | 'archivos'
    | 'revisiones'
    | 'especificaciones'
    | 'presupuesto'
    | 'eventos'
    | 'pliegos'
    | 'materiales'
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
    body: 'Carga DWG/DXF o adjuntos en Archivos. Cuando estén cargados, avanza la fase.',
    tabId: 'archivos',
    cta: 'Ir a Archivos',
  },
  FILES_INGESTED: {
    title: 'Archivos listos',
    body: 'Revisa que los planos estén correctos y continúa hacia revisión de arquitectura.',
    tabId: 'flujo',
    cta: 'Ir a Flujo',
  },
  ARCHITECTURE_REVIEW: {
    title: 'Revisión de arquitectura',
    body: 'Registra la decisión (aprobado / rechazo / parcial) y las notas en Revisiones.',
    tabId: 'revisiones',
    cta: 'Ir a Revisiones',
  },
  SPECIFICATIONS: {
    title: 'Especificaciones del pliego',
    body: 'Escribe el resumen (mín. 10 caracteres) y guarda antes de pasar a presupuesto.',
    tabId: 'especificaciones',
    cta: 'Ir a Especificaciones',
  },
  BUDGETING_PIPELINE: {
    title: 'Pipeline de presupuesto',
    body: 'Marca cotizaciones, volumetría y análisis; registra cotizaciones de subcontratos si aplica.',
    tabId: 'presupuesto',
    cta: 'Ir a Presupuesto',
  },
  BUDGET_APPROVED: {
    title: 'Pliego y materiales',
    body: 'Arma secciones (tiradas / planos / fases) en Pliegos y la cubicación en Materiales. Exporta Excel/PDF cuando convenga.',
    tabId: 'pliegos',
    cta: 'Ir a Pliegos',
  },
}
