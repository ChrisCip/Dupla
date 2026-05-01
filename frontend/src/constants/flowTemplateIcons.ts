/** Lucide icon component names allowed for workflow templates (must match backend). */
export const FLOW_TEMPLATE_ICON_KEYS = [
  'GitBranch',
  'Workflow',
  'Layers',
  'Boxes',
  'Kanban',
  'LayoutGrid',
  'CircleDot',
  'ArrowRight',
  'GitFork',
  'Route',
  'Map',
  'Building2',
  'HardHat',
  'DraftingCompass',
  'Ruler',
  'Hammer',
  'ClipboardList',
  'CheckCircle',
  'CirclePlay',
  'Timer',
  'Zap',
] as const

export type FlowTemplateIconKey = (typeof FLOW_TEMPLATE_ICON_KEYS)[number]

export const DEFAULT_FLOW_TEMPLATE_ICON: FlowTemplateIconKey = 'GitBranch'

export function coerceFlowTemplateIconKey(name: string | undefined): FlowTemplateIconKey {
  const k = name ?? ''
  if ((FLOW_TEMPLATE_ICON_KEYS as readonly string[]).includes(k)) return k as FlowTemplateIconKey
  return DEFAULT_FLOW_TEMPLATE_ICON
}
