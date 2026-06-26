import type { ClashRow, Severity } from '../types/clashWorkflow'

export const SEVERITY_LABELS_ES: Record<Severity, string> = {
  critical: 'Crítica',
  high: 'Alta',
  medium: 'Media',
  low: 'Baja',
}

export function incidentTitle(row: Pick<ClashRow, 'title_semantic' | 'clash_code'>): string {
  const semantic = row.title_semantic?.trim()
  return semantic || row.clash_code
}

export function incidentSubtitle(row: Pick<ClashRow, 'short_label' | 'clash_code'>): string | null {
  const label = row.short_label?.trim()
  return label || null
}

export function severityDisplayLabel(row: Pick<ClashRow, 'severity' | 'severity_label'>): string {
  const fromBackend = row.severity_label?.trim()
  if (fromBackend) return fromBackend
  return SEVERITY_LABELS_ES[row.severity] ?? row.severity
}
