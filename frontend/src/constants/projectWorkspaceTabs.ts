/**
 * Pestañas del workspace de proyecto (`ProjectWorkspacePage`).
 * `hub` es la vista de inicio (rejilla); no tiene formulario propio.
 */
const TAB_DEFS: { id: string; label: string }[] = [
  { id: 'hub', label: 'Inicio' },
  { id: 'detalles', label: 'Detalles' },
  { id: 'flujo', label: 'Flujo' },
  { id: 'archivos', label: 'Archivos' },
  { id: 'entregaPlanos', label: 'Control de entregas' },
  { id: 'revisiones', label: 'Revisiones' },
  { id: 'hallazgos', label: 'Hallazgos' },
  { id: 'pliego', label: 'Pliego' },
  { id: 'presupuestoMaestro', label: 'Presupuesto maestro' },
  { id: 'eventos', label: 'Eventos' },
]

export function projectWorkspaceTabs(): { id: string; label: string }[] {
  return TAB_DEFS.map(({ id, label }) => ({ id, label }))
}

/** Pestañas con panel de contenido (excluye inicio). */
export function projectWorkspaceSectionTabs(): { id: string; label: string }[] {
  return TAB_DEFS.filter((t) => t.id !== 'hub').map(({ id, label }) => ({ id, label }))
}
