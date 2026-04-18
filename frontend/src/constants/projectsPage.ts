import type { LucideIcon } from 'lucide-react'
import {
  BadgeCheck,
  Calculator,
  FileText,
  Inbox,
  ListChecks,
  PackageCheck,
  PencilRuler,
  ShieldCheck,
} from 'lucide-react'

import { WORKFLOW_PHASE_ORDER } from './workflowPhases'

export const PROJECT_CARD_MIME = 'application/x-dupla-project'

export const PROJECT_BOARD_PHASE_ICONS: Record<(typeof WORKFLOW_PHASE_ORDER)[number], LucideIcon> = {
  BOOTSTRAPPING: ListChecks,
  AWAITING_FILES: Inbox,
  FILES_INGESTED: PackageCheck,
  ARCHITECTURE_REVIEW: PencilRuler,
  SPECIFICATIONS: FileText,
  BUDGETING_PIPELINE: Calculator,
  MANAGEMENT_APPROVAL: ShieldCheck,
  BUDGET_APPROVED: BadgeCheck,
}

export function formatProjectUpdatedAt(iso: string | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('es', { dateStyle: 'short', timeStyle: 'short' })
}
