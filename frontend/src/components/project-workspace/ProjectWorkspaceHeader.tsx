import { useState } from 'react'
import { Link } from 'react-router-dom'

import { apiFetch } from '../../api/client'
import { PrimaryButton } from '../PrimaryButton'
import { StatusBadge } from '../StatusBadge'
import { downloadBlob, filenameFromContentDisposition } from '../../lib/download'

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

type ProjectWorkspaceHeaderProps = {
  displayTitle: string
  phaseLabel: string
  projectUuid: string
  token: string | null
  status: SaveStatus
  lastSavedAt: string | null
  lastError: string | null
  onOpenConfig: () => void
}

export function ProjectWorkspaceHeader({
  displayTitle,
  phaseLabel,
  projectUuid,
  token,
  status,
  lastSavedAt,
  lastError,
  onOpenConfig,
}: ProjectWorkspaceHeaderProps) {
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
    <header className="shrink-0 space-y-3 border-b border-black/10 pb-3 md:space-y-4 md:pb-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="du-meta">
            <Link className="du-link text-base" to="/app/projects">
              ← Volver a proyectos
            </Link>
          </div>
          <h1
            id="workspace-heading"
            className="mt-1 text-xl font-bold tracking-tight text-ink md:text-2xl"
          >
            {displayTitle}
          </h1>
          <p className="mt-0.5 du-meta">{phaseLabel ? `Fase: ${phaseLabel}` : 'Cargando fase…'}</p>
        </div>
        <div className="flex w-full shrink-0 flex-col items-stretch gap-2 sm:w-auto sm:items-end">
          <StatusBadge status={status} lastSavedAt={lastSavedAt} errorMessage={lastError} />
          <div className="flex w-full flex-wrap items-stretch justify-end gap-2 sm:w-auto sm:items-center">
            <button
              type="button"
              onClick={onOpenConfig}
              className="inline-flex min-h-[2.75rem] flex-1 items-center justify-center gap-2 rounded-lg border border-black/15 bg-white px-4 py-2.5 text-base font-medium text-ink shadow-sm hover:bg-black/[0.03] sm:flex-initial"
              aria-label="Configuración del proyecto"
            >
              <svg
                className="h-5 w-5 shrink-0 text-muted"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
              >
                <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
              Configuración
            </button>
            <details className="group relative flex-1 sm:flex-initial">
              <summary className="flex min-h-[2.75rem] cursor-pointer list-none items-center justify-center gap-1.5 rounded-lg border border-black/15 bg-white px-4 py-2.5 text-center text-base font-medium text-ink shadow-sm hover:bg-black/[0.03] [&::-webkit-details-marker]:hidden">
                Exportaciones
                <span className="hidden text-sm text-muted sm:inline">(Excel / PDF)</span>
                <svg
                  className="h-5 w-5 shrink-0 text-muted"
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
                <p className="text-sm text-muted">
                  Pueden tardar unos segundos; el botón muestra «Generando…» mientras descarga.
                </p>
                <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                  <PrimaryButton
                    type="button"
                    className="w-full justify-center sm:w-auto"
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
                    className="w-full justify-center sm:w-auto"
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
                    className="w-full justify-center sm:w-auto"
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
                    className="w-full justify-center sm:w-auto"
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
                </div>
              </div>
            </details>
          </div>
        </div>
      </div>
    </header>
  )
}
