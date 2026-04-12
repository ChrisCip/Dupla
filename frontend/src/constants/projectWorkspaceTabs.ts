import { WORKFLOW_PHASE_ORDER } from './workflowPhases'

const TAB_LABELS: Record<string, string> = {
  detalles: 'Detalles',
  flujo: 'Flujo',
  revisiones: 'Revisiones',
  archivos: 'Archivos',
  especificaciones: 'Pliego de condiciones',
  presupuesto: 'Presupuesto',
  pliegos: 'Pliegos',
  materiales: 'Materiales',
  eventos: 'Eventos',
}

/** Minimum phase index (in WORKFLOW_PHASE_ORDER) required to show the tab. */
const TAB_MIN_PHASE_INDEX: Record<string, number> = {
  detalles: 0,
  flujo: 0,
  revisiones: 0,
  archivos: 1,
  especificaciones: 4,
  presupuesto: 5,
  pliegos: 6,
  materiales: 6,
  eventos: 5,
}

const ORDERED_IDS = [
  'detalles',
  'flujo',
  'revisiones',
  'archivos',
  'especificaciones',
  'presupuesto',
  'pliegos',
  'materiales',
  'eventos',
] as const

export function visibleWorkspaceTabs(
  workflowPhase: string,
  options: { isMaster: boolean },
): { id: string; label: string }[] {
  const idx = WORKFLOW_PHASE_ORDER.indexOf(workflowPhase as (typeof WORKFLOW_PHASE_ORDER)[number])
  const active = idx >= 0 ? idx : 0
  const out: { id: string; label: string }[] = []
  for (const id of ORDERED_IDS) {
    if (id === 'eventos' && !options.isMaster) {
      continue
    }
    if (TAB_MIN_PHASE_INDEX[id] <= active) {
      out.push({ id, label: TAB_LABELS[id] ?? id })
    }
  }
  return out
}
