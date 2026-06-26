import { beforeEach, describe, expect, it, vi } from 'vitest'

import { downloadFinalHumanPdf } from './clashWorkflow'
import { downloadClashHumanPdf } from './structuralAnalysis'
import { apiFetch } from './client'

vi.mock('./client', () => ({
  apiFetch: vi.fn(() =>
    Promise.resolve({
      ok: true,
      blob: () => Promise.resolve(new Blob(['pdf'], { type: 'application/pdf' })),
      headers: { get: () => null },
    }),
  ),
}))

vi.mock('../lib/download', () => ({
  downloadBlob: vi.fn(),
  filenameFromContentDisposition: vi.fn(() => 'report.pdf'),
}))

describe('clash report download endpoints', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockClear()
  })

  it('downloadClashHumanPdf requests human.pdf', async () => {
    await downloadClashHumanPdf('proj-1', 'tok', 'job-42')
    expect(apiFetch).toHaveBeenCalledWith(
      '/api/projects/proj-1/clash/jobs/job-42/exports/human.pdf',
      { token: 'tok' },
    )
  })

  it('downloadFinalHumanPdf requests final-human.pdf', async () => {
    await downloadFinalHumanPdf('proj-1', 'tok')
    expect(apiFetch).toHaveBeenCalledWith(
      '/api/projects/proj-1/clash/jobs/latest/exports/final-human.pdf',
      { token: 'tok' },
    )
  })
})
