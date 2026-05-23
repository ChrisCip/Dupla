import { useMemo, useRef, useState } from 'react'

import { ChevronDown, ChevronRight, Download, Printer } from 'lucide-react'

import { apiFetch } from '../api/client'
import { PLIEGO_ITEM_ESTADO_OPTIONS, pliegoEstadoLabel } from '../constants/pliegoItemEstado'
import { PLIEGO_GA_FO_01_ARQUITECTURA } from '../data/pliegoGaFo01Arquitectura'
import { pliegoProgressPercent } from '../lib/pliegoFormState'
import type { PliegoItemEstado, PliegoItemState } from '../types/pliegoForm'

import { PrimaryButton } from './PrimaryButton'

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  )
}

function estadoTone(st: PliegoItemEstado): string {
  switch (st) {
    case 'COMPLETO':
      return 'border-emerald-700/25 bg-emerald-50 text-emerald-900'
    case 'INCOMPLETO':
      return 'border-amber-600/30 bg-amber-50 text-amber-950'
    case 'EN_REVISION':
      return 'border-sky-600/25 bg-sky-50 text-sky-950'
    case 'NO_APLICA':
      return 'border-black/10 bg-black/[0.04] text-muted'
    default:
      return 'border-black/10 bg-white text-muted'
  }
}

type Props = {
  projectUuid: string
  token: string | null
  documentTitle: string
  itemStates: Record<string, PliegoItemState>
  onItemStatesChange: (next: Record<string, PliegoItemState>) => void
  onPersist: () => Promise<void>
  persistBusy: boolean
  flowMsg: string | null
  onExportPdf?: () => void
  onExportXlsx?: () => void
}

export function PliegoCondicionesForm({
  projectUuid,
  token,
  documentTitle,
  itemStates,
  onItemStatesChange,
  onPersist,
  persistBusy,
  flowMsg,
  onExportPdf,
  onExportXlsx,
}: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {}
    PLIEGO_GA_FO_01_ARQUITECTURA.secciones.forEach((s, i) => {
      init[s.id] = i < 2
    })
    return init
  })
  const [uploadingId, setUploadingId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [pendingItemId, setPendingItemId] = useState<string | null>(null)

  const progress = useMemo(() => pliegoProgressPercent(itemStates), [itemStates])

  function patchItem(itemId: string, partial: Partial<PliegoItemState>) {
    const prev = itemStates[itemId] ?? { estado: 'PENDIENTE' as const, notas: '', file_uuid: null, file_name: null }
    onItemStatesChange({
      ...itemStates,
      [itemId]: { ...prev, ...partial },
    })
  }

  function openFilePicker(itemId: string) {
    setPendingItemId(itemId)
    fileInputRef.current?.click()
  }

  async function onFileSelected(files: FileList | null) {
    const itemId = pendingItemId
    setPendingItemId(null)
    if (!files?.[0] || !itemId || !token) return
    setUploadingId(itemId)
    try {
      const fd = new FormData()
      fd.append('file', files[0])
      fd.append('category', `pliego-ga-fo-01:${itemId}`)
      const res = await apiFetch(`/api/projects/${projectUuid}/files`, {
        method: 'POST',
        token,
        body: fd,
      })
      if (!res.ok) return
      const body = (await res.json()) as { uuid: string; original_name: string }
      patchItem(itemId, { file_uuid: body.uuid, file_name: body.original_name })
    } finally {
      setUploadingId(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  function toggleSection(id: string) {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  return (
    <div className="min-w-0 flex-1">
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        aria-hidden
        onChange={(e) => void onFileSelected(e.target.files)}
      />

      <div className="overflow-hidden rounded-xl border border-black/10 bg-white shadow-[var(--shadow-card)]">
        <header className="border-b border-black/8 bg-white px-5 py-5 sm:px-6 sm:py-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-primary">Documento técnico</p>
              <h2 className="mt-1.5 text-xl font-bold tracking-tight text-ink sm:text-2xl">{documentTitle}</h2>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
                GA-FO-01 Arquitectura: checklist de documentos por sección. Marca cada ítem como Completo o No aplica y
                adjunta archivos cuando corresponda.
              </p>
            </div>
            {(onExportPdf || onExportXlsx) && (
              <div className="flex shrink-0 flex-wrap items-center gap-2">
                {onExportPdf ? (
                  <button
                    type="button"
                    className="inline-flex size-10 items-center justify-center rounded-lg border border-black/12 bg-white text-ink shadow-sm transition hover:border-black/20 hover:bg-black/[0.02]"
                    onClick={onExportPdf}
                    aria-label="Exportar pliego en PDF"
                  >
                    <Printer className="size-[18px] text-primary" strokeWidth={2} aria-hidden />
                  </button>
                ) : null}
                {onExportXlsx ? (
                  <button
                    type="button"
                    className="inline-flex size-10 items-center justify-center rounded-lg border border-black/12 bg-white text-ink shadow-sm transition hover:border-black/20 hover:bg-black/[0.02]"
                    onClick={onExportXlsx}
                    aria-label="Exportar pliego en Excel"
                  >
                    <Download className="size-[18px] text-primary" strokeWidth={2} aria-hidden />
                  </button>
                ) : null}
              </div>
            )}
          </div>
          {flowMsg ? <p className="mt-3 text-sm font-medium text-primary">{flowMsg}</p> : null}
          <div className="mt-5 flex flex-wrap items-end justify-between gap-3 border-t border-black/6 pt-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Avance del checklist</p>
              <p className="mt-0.5 text-xs text-muted">Completo / No aplica sobre el total de documentos</p>
            </div>
            <span className="text-2xl font-semibold tabular-nums text-ink">{progress}%</span>
          </div>
          <div className="mt-2.5 h-1.5 rounded-full bg-black/[0.07]">
            <div
              className="h-1.5 rounded-full bg-primary transition-[width] duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </header>

        <div className="divide-y divide-black/8">
          {PLIEGO_GA_FO_01_ARQUITECTURA.secciones.map((sec, secIdx) => {
            const isOpen = expanded[sec.id] ?? false
            const numLabel = String(secIdx + 1).padStart(2, '0')
            return (
              <section key={sec.id} className="bg-white">
                <h3 className="m-0">
                  <button
                    type="button"
                    onClick={() => toggleSection(sec.id)}
                    aria-expanded={isOpen}
                    className="flex w-full items-center gap-3 bg-black/[0.025] px-4 py-3.5 text-left transition-colors hover:bg-black/[0.04] sm:px-5"
                  >
                    <span
                      className="flex size-8 shrink-0 items-center justify-center rounded bg-primary text-[11px] font-bold text-white"
                      aria-hidden
                    >
                      {numLabel}
                    </span>
                    <span className="min-w-0 flex-1 text-sm font-semibold leading-snug text-ink sm:text-[15px]">
                      {sec.titulo}
                    </span>
                    <span className="shrink-0 text-[11px] tabular-nums text-muted">{sec.items.length} docs</span>
                    <span className="flex size-8 shrink-0 items-center justify-center text-muted" aria-hidden>
                      {isOpen ? (
                        <ChevronDown className="size-5" strokeWidth={2} />
                      ) : (
                        <ChevronRight className="size-5" strokeWidth={2} />
                      )}
                    </span>
                  </button>
                </h3>
                {isOpen ? (
                  <ul className="m-0 list-none divide-y divide-black/6 border-t border-black/6 bg-white p-0">
                    {sec.items.map((it) => {
                      const st = itemStates[it.id] ?? {
                        estado: 'PENDIENTE' as const,
                        notas: '',
                        file_uuid: null,
                        file_name: null,
                      }
                      const busy = uploadingId === it.id
                      return (
                        <li
                          key={it.id}
                          className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start sm:justify-between sm:px-5"
                        >
                          <div className="min-w-0 flex-1">
                            <span className="font-mono text-[11px] font-medium text-primary">{it.id}</span>
                            <p className="mt-0.5 text-sm font-medium leading-snug text-ink">{it.nombre}</p>
                            <span
                              className={`mt-2 inline-flex rounded-md border px-2 py-0.5 text-[11px] font-medium ${estadoTone(st.estado)}`}
                            >
                              {pliegoEstadoLabel(st.estado)}
                            </span>
                          </div>
                          <div className="flex w-full shrink-0 flex-col gap-2 sm:w-52">
                            <label className="block text-[11px] font-medium text-muted">
                              Estado
                              <select
                                className="du-input mt-1 w-full py-2 text-sm"
                                value={st.estado}
                                onChange={(e) => patchItem(it.id, { estado: e.target.value as PliegoItemEstado })}
                              >
                                {PLIEGO_ITEM_ESTADO_OPTIONS.map((o) => (
                                  <option key={o.value} value={o.value}>
                                    {o.label}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <div className="flex flex-wrap items-center gap-2">
                              <button
                                type="button"
                                className="inline-flex items-center gap-2 rounded-lg border border-black/12 bg-black/[0.03] px-3 py-2 text-sm font-medium text-ink transition hover:bg-black/[0.06] disabled:opacity-50"
                                disabled={busy || !token}
                                onClick={() => openFilePicker(it.id)}
                                aria-label={`Adjuntar archivo para ${it.id}`}
                              >
                                <UploadIcon className="text-primary" />
                                {busy ? 'Subiendo…' : 'Adjuntar'}
                              </button>
                              {st.file_uuid && st.file_name ? (
                                <a
                                  className="max-w-[10rem] truncate text-xs font-medium text-primary underline-offset-2 hover:underline sm:max-w-[12rem]"
                                  href={`/api/projects/${projectUuid}/files/${st.file_uuid}/download`}
                                  title={st.file_name}
                                  onClick={async (e) => {
                                    e.preventDefault()
                                    if (!token) return
                                    const res = await apiFetch(
                                      `/api/projects/${projectUuid}/files/${st.file_uuid}/download`,
                                      { token },
                                    )
                                    if (!res.ok) return
                                    const blob = await res.blob()
                                    const url = URL.createObjectURL(blob)
                                    const a = document.createElement('a')
                                    a.href = url
                                    a.download = st.file_name ?? 'archivo'
                                    a.click()
                                    URL.revokeObjectURL(url)
                                  }}
                                >
                                  {st.file_name}
                                </a>
                              ) : (
                                <span className="text-[11px] text-muted">Sin archivo</span>
                              )}
                            </div>
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                ) : null}
              </section>
            )
          })}
        </div>

        <footer className="flex flex-wrap items-center gap-3 border-t border-black/8 bg-black/[0.02] px-5 py-4 sm:px-6">
          <PrimaryButton type="button" disabled={persistBusy} onClick={() => void onPersist()}>
            {persistBusy ? 'Guardando…' : 'Guardar pliego de condiciones'}
          </PrimaryButton>
          <span className="text-xs text-muted">Guarda para registrar el checklist en el proyecto.</span>
        </footer>
      </div>
    </div>
  )
}
