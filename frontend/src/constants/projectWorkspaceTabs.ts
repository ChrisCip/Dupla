/**
 * Pestañas del workspace de proyecto (`ProjectWorkspacePage`).
 * Todas las secciones están disponibles con independencia de la fase del flujo.
 */
const TAB_DEFS: { id: string; label: string }[] = [
  { id: 'detalles', label: 'Detalles' },
  { id: 'flujo', label: 'Flujo' },
  { id: 'archivos', label: 'Archivos' },
  { id: 'entregaPlanos', label: 'Entrega planos' },
  { id: 'revisiones', label: 'Revisiones' },
  { id: 'especificaciones', label: 'Especificaciones' },
  { id: 'presupuesto', label: 'Presupuesto' },
  { id: 'eventos', label: 'Eventos' },
  { id: 'pliegos', label: 'Pliegos' },
  { id: 'materiales', label: 'Materiales' },
]

export function projectWorkspaceTabs(): { id: string; label: string }[] {
  return TAB_DEFS.map(({ id, label }) => ({ id, label }))
}
