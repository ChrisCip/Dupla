import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { IncidentVisualPreview } from './IncidentVisualPreview'

vi.mock('../../api/client', () => ({
  apiFetch: vi.fn(() =>
    Promise.resolve({
      ok: true,
      blob: () => Promise.resolve(new Blob(['<svg></svg>'], { type: 'image/svg+xml' })),
    }),
  ),
}))

describe('IncidentVisualPreview', () => {
  it('shows warning when has_real_visual is false', () => {
    render(
      <IncidentVisualPreview
        token="tok"
        hasRealVisual={false}
        composedFullPageUrl="/api/tiles/composed.svg"
        zoomUrl="/api/tiles/zoom.svg"
      />,
    )
    expect(screen.getByRole('status')).toHaveTextContent('Visual real no disponible. Revisar anexo técnico.')
    expect(screen.queryByText('Zoom (inset secundario)')).not.toBeInTheDocument()
  })

  it('renders composed as main visual when has_real_visual is true', async () => {
    render(
      <IncidentVisualPreview
        token="tok"
        hasRealVisual={true}
        composedFullPageUrl="/api/tiles/composed.svg"
        title="INC-001"
      />,
    )
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(await screen.findByAltText('Visual INC-001')).toBeInTheDocument()
  })

  it('shows zoom only as secondary inset', async () => {
    render(
      <IncidentVisualPreview
        token="tok"
        hasRealVisual={true}
        composedFullPageUrl="/api/tiles/composed.svg"
        zoomUrl="/api/tiles/zoom.svg"
        title="INC-002"
      />,
    )
    expect(screen.getByText('Zoom (inset secundario)')).toBeInTheDocument()
    expect(await screen.findByAltText('Visual INC-002 zoom')).toBeInTheDocument()
  })

  it('does not crash when visual URLs are missing', () => {
    render(<IncidentVisualPreview token={null} hasRealVisual={true} />)
    expect(screen.getByText('Sin vista SVG para esta incidencia')).toBeInTheDocument()
  })
})
