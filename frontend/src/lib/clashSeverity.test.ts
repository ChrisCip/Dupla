import { describe, expect, it } from 'vitest'

import { SEVERITY_CLASSES } from './clashWorkflowLabels'
import { incidentTitle, severityDisplayLabel } from './clashSeverity'
import type { ClashRow, Severity } from '../types/clashWorkflow'

function row(partial: Partial<ClashRow> & Pick<ClashRow, 'clash_code' | 'severity'>): ClashRow {
  return {
    id: '1',
    job_id: 'j1',
    priority: 'P2',
    report_confidence: 'high',
    status: 'detected',
    status_label: 'Detectado',
    reviewer_decision: null,
    decision_label: null,
    dwg_a: 'A.dwg',
    dwg_b: 'B.dwg',
    level_id: 'P1',
    discipline_a: 'ARQ',
    discipline_b: 'EST',
    discipline_pair: 'ARQ / EST',
    layer_a: 'L1',
    layer_b: 'L2',
    layers_involved: 'L1 / L2',
    observation: null,
    recommended_action: null,
    action_owner: null,
    assigned_to: null,
    member_count: 1,
    area_mm2: 1,
    overlap_depth_mm: 1,
    location: {
      unit: 'mm',
      model_centroid: { x: 0, y: 0, space: 'model' },
      world_centroid: { x: 0, y: 0, space: 'world' },
      world_bounds: { min: { x: 0, y: 0 }, max: { x: 1, y: 1 } },
      alignment_offset_mm: null,
      autocad_zoom_window_command: 'Z W',
    },
    updated_at: null,
    created_at: null,
    ...partial,
  }
}

describe('clashSeverity helpers', () => {
  it('uses title_semantic when present', () => {
    expect(
      incidentTitle(row({ clash_code: 'incident_0001', severity: 'low', title_semantic: 'ARQ_BASE / INC-001' })),
    ).toBe('ARQ_BASE / INC-001')
  })

  it('falls back to clash_code', () => {
    expect(incidentTitle(row({ clash_code: 'legacy_001', severity: 'low' }))).toBe('legacy_001')
  })

  it('prefers severity_label from backend', () => {
    expect(
      severityDisplayLabel(row({ clash_code: 'x', severity: 'critical', severity_label: 'Crítica confirmada' })),
    ).toBe('Crítica confirmada')
  })

  it('maps low severity label to Baja in Spanish fallback', () => {
    expect(severityDisplayLabel(row({ clash_code: 'x', severity: 'low' }))).toBe('Baja')
  })
})

describe('SEVERITY_CLASSES', () => {
  it('uses blue styling for low severity', () => {
    expect(SEVERITY_CLASSES.low).toContain('blue')
  })

  it('covers all severity levels', () => {
    const levels: Severity[] = ['critical', 'high', 'medium', 'low']
    for (const level of levels) {
      expect(SEVERITY_CLASSES[level]).toBeTruthy()
    }
  })
})
