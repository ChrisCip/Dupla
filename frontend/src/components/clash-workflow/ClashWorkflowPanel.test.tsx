import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { ClashRow } from '../../types/clashWorkflow'
import { ClashWorkflowPanel } from './ClashWorkflowPanel'

const mockRow: ClashRow = {
  id: 'row-1',
  clash_code: 'incident_0001',
  job_id: 'job-1',
  priority: 'P2',
  severity: 'high',
  severity_label: 'Alta',
  title_semantic: 'ARQ-01_BASE / INC-001 / Contra HID / Severidad alta',
  short_label: 'INC-001: Coordinar desvío',
  table_comment: 'Observación larga de prueba para la tabla de incidencias.',
  base_plan_number: 'ARQ-01',
  compared_plan_number: 'HID-01',
  report_confidence: 'high',
  status: 'detected',
  status_label: 'Detectado',
  reviewer_decision: null,
  decision_label: null,
  dwg_a: 'ARQ-01.dwg',
  dwg_b: 'HID-01.dwg',
  level_id: 'P1',
  discipline_a: 'ARQUITECTURA',
  discipline_b: 'PLOMERIA',
  discipline_pair: 'ARQUITECTURA / PLOMERIA',
  layer_a: 'ARQ_MURO',
  layer_b: 'HID_TUB',
  layers_involved: 'ARQ_MURO / HID_TUB',
  observation: null,
  recommended_action: 'Coordinar desvío',
  action_owner: null,
  assigned_to: null,
  member_count: 1,
  area_mm2: 50000,
  overlap_depth_mm: 100,
  location: {
    unit: 'mm',
    model_centroid: { x: 0, y: 0, space: 'model' },
    world_centroid: { x: 0, y: 0, space: 'world' },
    world_bounds: { min: { x: 0, y: 0 }, max: { x: 1, y: 1 } },
    alignment_offset_mm: null,
    autocad_zoom_window_command: 'Z W 0,0 1,1',
  },
  updated_at: null,
  created_at: null,
}

vi.mock('../../api/clashWorkflow', () => ({
  addClashWorkflowComment: vi.fn(),
  getClashWorkflowDashboard: vi.fn(() =>
    Promise.resolve({
      job_id: 'job-1',
      total_clashes: 1,
      by_severity: { critical: 0, high: 1, medium: 0, low: 0 },
      by_priority: {},
      by_status: {},
      pending_reviewer_decisions: 0,
      correction_uploaded: 0,
      pending_reanalysis: 0,
      resolved: 0,
      false_positives: 0,
      still_present_after_reanalysis: 0,
    }),
  ),
  getClashWorkflowFilters: vi.fn(() =>
    Promise.resolve({
      priorities: ['P2'],
      statuses: ['detected'],
      severities: ['high'],
      levels: ['P1'],
      disciplines: [],
      reviewers: [],
      dwgs: [],
    }),
  ),
  getClashWorkflowDetail: vi.fn(),
  listClashWorkflowRows: vi.fn(() => Promise.resolve([mockRow])),
  recordClashWorkflowDecision: vi.fn(),
  requestClashReanalysis: vi.fn(),
  updateClashWorkflowStatus: vi.fn(),
  uploadClashCorrection: vi.fn(),
}))

describe('ClashWorkflowPanel', () => {
  it('shows title_semantic and short_label in the table', async () => {
    render(<ClashWorkflowPanel projectUuid="proj-1" token="tok" visible />)
    expect(await screen.findByText(mockRow.title_semantic!)).toBeInTheDocument()
    expect(screen.getByText(mockRow.short_label!)).toBeInTheDocument()
    expect(screen.getByText('incident_0001')).toBeInTheDocument()
  })

  it('shows Spanish severity label in the table', async () => {
    render(<ClashWorkflowPanel projectUuid="proj-1" token="tok" visible />)
    const table = await screen.findByRole('table')
    expect(within(table).getByText('Alta')).toBeInTheDocument()
  })
})
