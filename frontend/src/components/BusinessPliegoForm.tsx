import { useMemo, useState } from 'react'
import { ChevronRight, Printer, Download } from 'lucide-react'

import {
  BUSINESS_PLIEGO_SECTION_KEYS,
  BUSINESS_PLIEGO_SECTION_LABELS,
  MIN_PLIEGO_SECTION_LEN,
  type BusinessPliegoSectionKey,
} from '../constants/businessPliego'

import { PrimaryButton } from './PrimaryButton'

type BusinessPliegoFormProps = {
  documentTitle: string
  sections: Record<BusinessPliegoSectionKey, string>
  onSectionChange: (key: BusinessPliegoSectionKey, value: string) => void
  specSummary: string
  onSpecSummaryChange: (value: string) => void
  onGenerate: (force: boolean) => Promise<void>
  generateBusy: boolean
  saveBusy: boolean
  onSave: () => Promise<void>
  approved: boolean
  generatedAt: string | null
  flowMsg: string | null
  onExportPdf?: () => void
  onExportXlsx?: () => void
}

export function BusinessPliegoForm({
  documentTitle,
  sections,
  onSectionChange,
  specSummary,
  onSpecSummaryChange,
  onGenerate,
  generateBusy,
  saveBusy,
  onSave,
  approved,
  generatedAt,
  flowMsg,
  onExportPdf,
  onExportXlsx,
}: BusinessPliegoFormProps) {
  const [open, setOpen] = useState<Record<string, boolean>>(() => {
    const o: Record<string, boolean> = {}
    BUSINESS_PLIEGO_SECTION_KEYS.forEach((k, i) => {
      o[k] = i < 2
    })
    return o
  })

  const materialLines = useMemo(() => {
    const raw = sections.materials ?? ''
    return raw
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean)
  }, [sections.materials])

  function toggle(key: BusinessPliegoSectionKey) {
    setOpen((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  function appendMaterialLine() {
    const cur = sections.materials ?? ''
    const next = cur.trim().length > 0 ? `${cur.trim()}\n` : ''
    onSectionChange('materials', `${next}Nuevo material técnico`)
  }

  return (
    <div className="relative overflow-hidden rounded-xl border border-black/10 bg-white shadow-[var(--shadow-card)] print:border-0 print:shadow-none">
      {!approved ? (
        <div
          className="pointer-events-none absolute inset-0 z-0 flex items-center justify-center overflow-hidden"
          aria-hidden
        >
          <span className="rotate-[-18deg] select-none text-[clamp(3rem,14vw,8rem)] font-black uppercase tracking-widest text-black/[0.045]">
            Borrador
          </span>
        </div>
      ) : null}

      <div className="relative z-10 border-b border-black/10 bg-white/95 px-4 py-4 sm:px-6 print:px-0">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-primary">Documento técnico</p>
            <h3 className="mt-1 text-xl font-bold tracking-tight text-ink sm:text-2xl">{documentTitle}</h3>
            {generatedAt ? (
              <p className="mt-1 text-xs text-muted">
                Borrador generado: {new Date(generatedAt).toLocaleString()}
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2 print:hidden">
            <button
              type="button"
              className="rounded-lg border border-black/12 p-2 text-muted transition hover:bg-black/[0.04] hover:text-ink"
              title="Imprimir"
              aria-label="Imprimir"
              onClick={() => window.print()}
            >
              <Printer className="size-5" strokeWidth={2} aria-hidden />
            </button>
            {onExportPdf ? (
              <button
                type="button"
                className="rounded-lg border border-black/12 p-2 text-muted transition hover:bg-black/[0.04] hover:text-ink"
                title="Descargar PDF"
                aria-label="Descargar PDF"
                onClick={onExportPdf}
              >
                <Download className="size-5" strokeWidth={2} aria-hidden />
              </button>
            ) : null}
            {onExportXlsx ? (
              <button
                type="button"
                className="rounded-lg border border-black/12 px-2 py-2 text-xs font-semibold text-ink transition hover:bg-black/[0.04]"
                onClick={onExportXlsx}
              >
                Excel
              </button>
            ) : null}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2 print:hidden">
          <button
            type="button"
            className="rounded-lg border border-primary/35 bg-primary/[0.08] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-primary hover:bg-primary/[0.12] disabled:opacity-50"
            disabled={generateBusy}
            onClick={() => void onGenerate(false)}
          >
            {generateBusy ? 'Generando…' : 'Generar borrador'}
          </button>
          <button
            type="button"
            className="rounded-lg border border-black/15 bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-black/[0.03] disabled:opacity-50"
            disabled={generateBusy}
            onClick={() => {
              if (
                window.confirm(
                  '¿Regenerar? Se reemplaza el borrador y se anula un pliego aprobado previo al guardar.',
                )
              ) {
                void onGenerate(true)
              }
            }}
          >
            Regenerar
          </button>
          <PrimaryButton type="button" disabled={saveBusy} onClick={() => void onSave()}>
            {saveBusy ? 'Guardando…' : 'Guardar'}
          </PrimaryButton>
        </div>
        {approved ? (
          <p className="mt-3 text-xs font-medium text-emerald-800">Pliego aprobado.</p>
        ) : null}
        {flowMsg ? <p className="mt-2 text-sm text-primary">{flowMsg}</p> : null}

        <div className="mt-4 border-t border-black/8 pt-4 print:hidden">
          <label className="text-xs font-semibold text-muted" htmlFor="bp-spec-summary">
            Resumen ejecutivo
          </label>
          <p className="mt-1 text-[11px] leading-relaxed text-muted">
            Texto corto para auditoría y exportaciones. Si el documento estructurado aún no está completo, este resumen
            puede usarse como respaldo para validar el avance de fase (mín. 10 caracteres).
          </p>
          <textarea
            id="bp-spec-summary"
            className="mt-2 min-h-[96px] w-full rounded-lg border border-black/12 bg-white p-3 text-sm leading-relaxed text-ink outline-none focus:border-primary/35 focus:ring-1 focus:ring-primary/25"
            value={specSummary}
            onChange={(e) => onSpecSummaryChange(e.target.value)}
            placeholder="Síntesis del alcance, supuestos y riesgos relevantes…"
            aria-label="Resumen ejecutivo del pliego"
          />
        </div>
      </div>

      <div className="relative z-10 divide-y divide-black/8 px-2 pb-4 pt-2 sm:px-4">
        {BUSINESS_PLIEGO_SECTION_KEYS.map((key, idx) => {
          const isOpen = open[key]
          const len = sections[key]?.trim().length ?? 0
          const short = len > 0 && len < MIN_PLIEGO_SECTION_LEN
          const num = String(idx + 1).padStart(2, '0')
          const label = BUSINESS_PLIEGO_SECTION_LABELS[key]

          return (
            <div key={key} className="bg-white">
              <button
                type="button"
                className="flex w-full items-center gap-3 px-2 py-3 text-left transition hover:bg-black/[0.02] sm:px-3"
                aria-expanded={isOpen}
                onClick={() => toggle(key)}
              >
                <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary text-xs font-bold text-white">
                  {num}
                </span>
                <span className="min-w-0 flex-1 font-semibold text-ink">{label}</span>
                {short ? (
                  <span className="hidden text-xs text-amber-700 sm:inline">Texto corto</span>
                ) : null}
                <ChevronRight
                  className={`size-5 shrink-0 text-muted transition-transform ${isOpen ? 'rotate-90' : ''}`}
                  aria-hidden
                />
              </button>
              {isOpen ? (
                <div className="border-t border-black/6 px-3 pb-4 pt-2 sm:px-5">
                  {key === 'materials' ? (
                    <div className="space-y-3">
                      <div className="grid gap-2 sm:grid-cols-2">
                        {materialLines.length === 0 ? (
                          <p className="text-sm text-muted">Añade materiales en el texto o con el botón.</p>
                        ) : (
                          materialLines.map((line) => (
                            <div
                              key={line}
                              className="rounded-lg border border-black/10 bg-black/[0.02] px-3 py-2 text-sm text-ink"
                            >
                              {line}
                            </div>
                          ))
                        )}
                      </div>
                      <button
                        type="button"
                        className="w-full rounded-lg border border-dashed border-black/20 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted transition hover:border-primary/35 hover:text-primary"
                        onClick={appendMaterialLine}
                      >
                        + Añadir material técnico
                      </button>
                      <label className="sr-only" htmlFor={`bp-${key}-textarea`}>
                        {label}
                      </label>
                      <textarea
                        id={`bp-${key}-textarea`}
                        className="min-h-[100px] w-full rounded-lg border border-black/12 p-3 text-sm text-ink outline-none focus:border-primary/35 focus:ring-1 focus:ring-primary/25"
                        placeholder="Un material por línea…"
                        value={sections[key] ?? ''}
                        onChange={(e) => onSectionChange(key, e.target.value)}
                      />
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-muted" htmlFor={`bp-${key}`}>
                        Contenido — mín. {MIN_PLIEGO_SECTION_LEN} caracteres
                      </label>
                      <textarea
                        id={`bp-${key}`}
                        className="min-h-[120px] w-full rounded-lg border border-black/12 p-3 text-sm leading-relaxed text-ink outline-none focus:border-primary/35 focus:ring-1 focus:ring-primary/25"
                        value={sections[key] ?? ''}
                        onChange={(e) => onSectionChange(key, e.target.value)}
                      />
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
