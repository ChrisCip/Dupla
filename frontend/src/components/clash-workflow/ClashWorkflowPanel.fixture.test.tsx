import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { ClashDetail, ClashRow } from '../../types/clashWorkflow'
import { ClashWorkflowPanel } from './ClashWorkflowPanel'

const baseLocation = {
  unit: 'mm',
  model_centroid: { x: 0, y: 0, space: 'model' },
  world_centroid: { x: 0, y: 0, space: 'world' },
  world_bounds: { min: { x: 0, y: 0 }, max: { x: 1, y: 1 } },
  alignment_offset_mm: null,
  autocad_zoom_window_command: 'Z W 0,0 1,1',
}

function row(partial: Partial<ClashRow> & Pick<ClashRow, 'id' | 'clash_code' | 'severity'>): ClashRow {
  return {
    job_id: 'job-1',
    priority: 'P2',
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
    recommended_action: null,
    action_owner: null,
    assigned_to: null,
    member_count: 1,
    area_mm2: 1,
    overlap_depth_mm: 1,
    location: baseLocation,
    updated_at: null,
    created_at: null,
    ...partial,
  }
}

const realVisualRow = row({
  id: 'real-1',
  clash_code: 'incident_0001',
  severity: 'high',
  severity_label: 'Alta',
  title_semantic: 'ARQ-01_BASE / INC-001 / Contra HID / Severidad alta',
  short_label: 'INC-001: Coordinar desvío',
  table_comment: 'Observación principal larga '.repeat(20),
  recommended_action: 'Coordinar desvío de tubería',
  base_plan_number: 'ARQ-01',
  compared_plan_number: 'HID-01',
})

const noVisualRow = row({
  id: 'novisual-1',
  clash_code: 'incident_0002',
  severity: 'critical',
  severity_label: 'Crítica',
  title_semantic: 'EST_BASE / INC-002 / Severidad crítica',
  short_label: 'INC-002: Sin visual',
  table_comment: 'Revisar anexo técnico manualmente.',
  base_plan_number: 'EST-01',
  compared_plan_number: 'MEP-01',
})

const legacyRow = row({
  id: 'legacy-1',
  clash_code: 'legacy_clash_0099',
  severity: 'low',
})

const realDetail: ClashDetail = {
  ...realVisualRow,
  audit_trail: [],
  corrections: [],
  visual_preview: {
    available: true,
    annotated_url: '/api/legacy/annotated.svg',
    plain_url: '/api/legacy/plain.svg',
    composed_full_page_url: '/api/tiles/composed.svg',
    base_full_plan_url: '/api/tiles/base.svg',
    overlay_url: '/api/tiles/overlay.svg',
    zoom_url: '/api/tiles/zoom.svg',
    default_url: '/api/legacy/default.svg',
    has_real_visual: true,
    visual_warnings: [],
    format: 'svg',
    description: 'composed',
  },
}

const noVisualDetail: ClashDetail = {
  ...noVisualRow,
  audit_trail: [],
  corrections: [],
  visual_preview: {
    available: false,
    annotated_url: '/api/legacy/annotated.svg',
    plain_url: '/api/legacy/plain.svg',
    composed_full_page_url: null,
    base_full_plan_url: null,
    overlay_url: null,
    zoom_url: '/api/tiles/zoom-only.svg',
    default_url: '/api/legacy/default.svg',
    has_real_visual: false,
    visual_warnings: ['Sin tile compuesto'],
    format: 'svg',
    description: 'none',
  },
}

const legacyDetail: ClashDetail = {
  ...legacyRow,
  audit_trail: [],
  corrections: [],
}

vi.mock('../../api/client', () => ({
  apiFetch: vi.fn(() =>
    Promise.resolve({
      ok: true,
      blob: () => Promise.resolve(new Blob(['<svg></svg>'], { type: 'image/svg+xml' })),
    }),
  ),
}))

vi.mock('../../api/clashWorkflow', () => ({
  addClashWorkflowComment: vi.fn(),
  getClashWorkflowDashboard: vi.fn(() =>
    Promise.resolve({
      job_id: 'job-1',
      total_clashes: 3,
      by_severity: { critical: 1, high: 1, medium: 0, low: 1 },
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
      severities: ['critical', 'high', 'low'],
      levels: ['P1'],
      disciplines: [],
      reviewers: [],
      dwgs: [],
    }),
  ),
  getClashWorkflowDetail: vi.fn((_, __, itemId: string) => {
    if (itemId === 'real-1') return Promise.resolve(realDetail)
    if (itemId === 'novisual-1') return Promise.resolve(noVisualDetail)
    return Promise.resolve(legacyDetail)
  }),
  listClashWorkflowRows: vi.fn(() => Promise.resolve([realVisualRow, noVisualRow, legacyRow])),
  recordClashWorkflowDecision: vi.fn(),
  requestClashReanalysis: vi.fn(),
  updateClashWorkflowStatus: vi.fn(),
  uploadClashCorrection: vi.fn(),
}))

describe('ClashWorkflowPanel fixture scenarios', () => {
  it('detail: table_comment, plans, recommended_action, composed main + zoom inset', async () => {
    const user = userEvent.setup()
    render(<ClashWorkflowPanel projectUuid="proj-1" token="tok" visible />)
    await user.click(await screen.findByText(realVisualRow.title_semantic!))
    const aside = screen.getAllByRole('complementary').at(-1)!
    expect(within(aside).getByText('Observación')).toBeInTheDocument()
    expect(within(aside).getByText(/Observación principal larga/)).toBeInTheDocument()
    expect(within(aside).getByText('Acción sugerida')).toBeInTheDocument()
    expect(within(aside).getByText('Coordinar desvío de tubería')).toBeInTheDocument()
    expect(within(aside).getByText('Plano base')).toBeInTheDocument()
    expect(within(aside).getByText('ARQ-01')).toBeInTheDocument()
    expect(within(aside).getByText('Plano comparado')).toBeInTheDocument()
    expect(within(aside).getByText('HID-01')).toBeInTheDocument()
    expect(within(aside).getByText('Zoom (inset secundario)')).toBeInTheDocument()
    expect(screen.queryByText('Anotado')).not.toBeInTheDocument()
    expect(screen.queryByText('Plano simple')).not.toBeInTheDocument()
  })

  it('detail: has_real_visual=false shows banner and no zoom inset', async () => {
    const user = userEvent.setup()
    render(<ClashWorkflowPanel projectUuid="proj-1" token="tok" visible />)
    await user.click(await screen.findByText(noVisualRow.title_semantic!))
    expect(screen.getByRole('status')).toHaveTextContent('Visual real no disponible. Revisar anexo técnico.')
    expect(screen.queryByText('Zoom (inset secundario)')).not.toBeInTheDocument()
    expect(screen.queryByAltText(/Visual/)).not.toBeInTheDocument()
  })

  it('list: legacy item falls back to clash_code', async () => {
    render(<ClashWorkflowPanel projectUuid="proj-1" token="tok" visible />)
    const table = await screen.findByRole('table')
    expect(within(table).getAllByText('legacy_clash_0099').length).toBeGreaterThan(0)
  })

  it('severity labels: Crítica, Alta, Baja in table badges', async () => {
    render(<ClashWorkflowPanel projectUuid="proj-1" token="tok" visible />)
    const table = await screen.findByRole('table')
    expect(within(table).getByText('Alta')).toBeInTheDocument()
    expect(within(table).getByText('Crítica')).toBeInTheDocument()
    expect(within(table).getByText('Baja')).toBeInTheDocument()
  })
})
