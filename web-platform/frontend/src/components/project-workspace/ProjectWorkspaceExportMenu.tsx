import { useState } from 'react'

import { apiFetch } from '../../api/client'
import { downloadBlob, filenameFromContentDisposition } from '../../lib/download'
import { PrimaryButton } from '../PrimaryButton'

type ProjectWorkspaceExportMenuProps = {
  projectUuid: string
  token: string | null
}

export function ProjectWorkspaceExportMenu({ projectUuid, token }: ProjectWorkspaceExportMenuProps) {
  const [exportBusy, setExportBusy] = useState<string | null>(null)

  async function exportFile(path: string, filename: string, busyKey: string) {
    if (!token) return
    setExportBusy(busyKey)
    try {
      const res = await apiFetch(path, { token })
      if (!res.ok) return
      const blob = await res.blob()
      downloadBlob(blob, filenameFromContentDisposition(res, filename))
    } finally {
      setExportBusy(null)
    }
  }

  return (
    <details className="group relative">
      <summary className="flex cursor-pointer list-none items-center gap-1.5 rounded-lg border border-black/12 bg-white px-3 py-2 text-sm font-semibold text-ink shadow-sm transition hover:bg-black/[0.03] [&::-webkit-details-marker]:hidden">
        Exportar
        <svg
          className="h-4 w-4 shrink-0 text-muted"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden
        >
          <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </summary>
      <div className="absolute right-0 top-full z-40 mt-1 w-[min(calc(100vw-2rem),22rem)] rounded-lg border border-black/10 bg-white p-4 text-left shadow-lg">
        <p className="text-xs text-muted">Puede tardar unos segundos en generarse.</p>
        <div className="mt-2 flex flex-col gap-2">
          <PrimaryButton
            type="button"
            className="w-full justify-center text-xs"
            disabled={exportBusy !== null}
            onClick={() =>
              void exportFile(
                `/api/projects/${projectUuid}/exports/pliego.xlsx`,
                `pliego-${projectUuid}.xlsx`,
                'pliego-xlsx',
              )
            }
          >
            {exportBusy === 'pliego-xlsx' ? 'Generando…' : 'Pliego (Excel)'}
          </PrimaryButton>
          <PrimaryButton
            type="button"
            className="w-full justify-center text-xs"
            disabled={exportBusy !== null}
            onClick={() =>
              void exportFile(
                `/api/projects/${projectUuid}/exports/pliego.pdf`,
                `pliego-${projectUuid}.pdf`,
                'pliego-pdf',
              )
            }
          >
            {exportBusy === 'pliego-pdf' ? 'Generando…' : 'Pliego (PDF)'}
          </PrimaryButton>
          <PrimaryButton
            type="button"
            className="w-full justify-center text-xs"
            disabled={exportBusy !== null}
            onClick={() =>
              void exportFile(
                `/api/projects/${projectUuid}/exports/control-planos.xlsx`,
                `control-planos-${projectUuid}.xlsx`,
                'control-xlsx',
              )
            }
          >
            {exportBusy === 'control-xlsx' ? 'Generando…' : 'Control planos (Excel)'}
          </PrimaryButton>
          <PrimaryButton
            type="button"
            className="w-full justify-center text-xs"
            disabled={exportBusy !== null}
            onClick={() =>
              void exportFile(
                `/api/projects/${projectUuid}/exports/control-planos.pdf`,
                `control-planos-${projectUuid}.pdf`,
                'control-pdf',
              )
            }
          >
            {exportBusy === 'control-pdf' ? 'Generando…' : 'Control planos (PDF)'}
          </PrimaryButton>
          <PrimaryButton
            type="button"
            className="w-full justify-center text-xs"
            disabled={exportBusy !== null}
            onClick={() =>
              void exportFile(
                `/api/projects/${projectUuid}/exports/documentary-report.pdf`,
                `informe-documental-${projectUuid}.pdf`,
                'doc-pdf',
              )
            }
          >
            {exportBusy === 'doc-pdf' ? 'Generando…' : 'Informe documental (PDF)'}
          </PrimaryButton>
        </div>
      </div>
    </details>
  )
}
