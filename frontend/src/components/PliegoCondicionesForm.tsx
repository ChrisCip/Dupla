import { useMemo, useRef, useState } from 'react'

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
  specSummary: string
  onSpecSummaryChange: (v: string) => void
  itemStates: Record<string, PliegoItemState>
  onItemStatesChange: (next: Record<string, PliegoItemState>) => void
  onPersist: () => Promise<void>
  persistBusy: boolean
  flowMsg: string | null
}

export function PliegoCondicionesForm({
  projectUuid,
  token,
  specSummary,
  onSpecSummaryChange,
  itemStates,
  onItemStatesChange,
  onPersist,
  persistBusy,
  flowMsg,
}: Props) {
  const [activeSection, setActiveSection] = useState<string>(
    PLIEGO_GA_FO_01_ARQUITECTURA.secciones[0]?.id ?? 'permisologia',
  )
  const [uploadingId, setUploadingId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [pendingItemId, setPendingItemId] = useState<string | null>(null)

  const progress = useMemo(() => pliegoProgressPercent(itemStates), [itemStates])

  const active = useMemo(
    () => PLIEGO_GA_FO_01_ARQUITECTURA.secciones.find((s) => s.id === activeSection),
    [activeSection],
  )

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

  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        aria-hidden
        onChange={(e) => void onFileSelected(e.target.files)}
      />

      <nav
        className="lg:w-64 lg:shrink-0 lg:sticky lg:top-4 lg:self-start"
        aria-label="Secciones del pliego"
      >
        <div className="rounded-lg border border-black/10 bg-white p-2 shadow-[var(--shadow-card)]">
          <p className="px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted">Secciones</p>
          <ul className="max-h-[50vh] space-y-0.5 overflow-y-auto lg:max-h-[calc(100vh-8rem)]">
            {PLIEGO_GA_FO_01_ARQUITECTURA.secciones.map((sec) => (
              <li key={sec.id}>
                <button
                  type="button"
                  onClick={() => setActiveSection(sec.id)}
                  className={`w-full rounded-md px-2 py-2 text-left text-sm transition-colors ${
                    activeSection === sec.id
                      ? 'bg-primary/10 font-medium text-ink ring-1 ring-primary/25'
                      : 'text-muted hover:bg-black/[0.03] hover:text-ink'
                  }`}
                >
                  {sec.titulo}
                </button>
              </li>
            ))}
          </ul>
        </div>
      </nav>

      <div className="min-w-0 flex-1 space-y-6">
        <div className="rounded-lg border border-black/10 bg-white p-4 shadow-[var(--shadow-card)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Progreso del checklist</p>
              <p className="mt-1 text-sm text-muted">
                Completo / No aplica frente al total de partidas (GA-FO-01).
              </p>
            </div>
            <span className="text-2xl font-semibold tabular-nums text-ink">{progress}%</span>
          </div>
          <div className="mt-3 h-2 rounded-full bg-black/[0.06]">
            <div
              className="h-2 rounded-full bg-primary/80 transition-[width] duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <div className="rounded-lg border border-black/10 bg-white p-2 shadow-[var(--shadow-card)]">
          <p className="px-3 py-2 text-sm text-muted">
            Este paso va <span className="font-medium text-ink">antes del presupuesto</span>. El resumen debe tener al
            menos 10 caracteres para avanzar la fase a Presupuesto en <strong className="text-ink">Flujo</strong>.
          </p>
          {flowMsg ? <p className="px-3 pb-2 text-sm text-primary">{flowMsg}</p> : null}
          <label htmlFor="spec-summary-ga" className="du-label px-3">
            Resumen ejecutivo del pliego
          </label>
          <textarea
            id="spec-summary-ga"
            className="du-input mx-3 mb-3 min-h-[120px] w-[calc(100%-1.5rem)] text-sm"
            value={specSummary}
            onChange={(e) => onSpecSummaryChange(e.target.value)}
            aria-label="Resumen del pliego de condiciones"
          />
        </div>

        {active ? (
          <section className="rounded-lg border border-black/10 bg-white shadow-[var(--shadow-card)]">
            <div className="border-b border-black/5 px-4 py-3">
              <h3 className="text-base font-semibold text-ink">{active.titulo}</h3>
              <p className="mt-0.5 text-xs text-muted">{active.items.length} partidas</p>
            </div>
            <ul className="divide-y divide-black/5">
              {active.items.map((it) => {
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
                    className="flex flex-col gap-3 px-4 py-4 transition-colors hover:bg-black/[0.015] sm:flex-row sm:items-start sm:justify-between"
                  >
                    <div className="min-w-0 flex-1">
                      <span className="font-mono text-[11px] text-primary">{it.id}</span>
                      <p className="text-sm font-medium leading-snug text-ink">{it.nombre}</p>
                      <span
                        className={`mt-2 inline-flex rounded-md border px-2 py-0.5 text-[11px] font-medium ${estadoTone(st.estado)}`}
                      >
                        {pliegoEstadoLabel(st.estado)}
                      </span>
                      <label className="mt-2 block text-[11px] text-muted">
                        Notas
                        <input
                          className="du-input mt-1 w-full py-1.5 text-sm"
                          value={st.notas ?? ''}
                          onChange={(e) => patchItem(it.id, { notas: e.target.value })}
                          placeholder="Observaciones…"
                        />
                      </label>
                    </div>
                    <div className="flex shrink-0 flex-col gap-2 sm:w-52">
                      <label className="block text-[11px] text-muted">
                        Estado
                        <select
                          className="du-input mt-1 w-full py-1.5 text-sm"
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
                          className="inline-flex items-center gap-2 rounded-md border border-black/10 bg-black/[0.03] px-3 py-2 text-sm font-medium text-ink hover:bg-black/[0.06] disabled:opacity-50"
                          disabled={busy || !token}
                          onClick={() => openFilePicker(it.id)}
                          aria-label={`Adjuntar archivo para ${it.id}`}
                        >
                          <UploadIcon className="text-primary" />
                          {busy ? 'Subiendo…' : 'Adjuntar'}
                        </button>
                        {st.file_uuid && st.file_name ? (
                          <a
                            className="text-xs font-medium text-primary underline-offset-2 hover:underline"
                            href={`/api/projects/${projectUuid}/files/${st.file_uuid}/download`}
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
          </section>
        ) : null}

        <div className="flex flex-wrap items-center gap-3">
          <PrimaryButton type="button" disabled={persistBusy} onClick={() => void onPersist()}>
            {persistBusy ? 'Guardando…' : 'Guardar pliego de condiciones'}
          </PrimaryButton>
          <span className="text-xs text-muted">
            Incluye el resumen y el estado de cada partida del GA-FO-01.
          </span>
        </div>
      </div>
    </div>
  )
}
