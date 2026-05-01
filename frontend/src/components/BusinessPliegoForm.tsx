import {
  BUSINESS_PLIEGO_SECTION_KEYS,
  BUSINESS_PLIEGO_SECTION_LABELS,
  MIN_PLIEGO_SECTION_LEN,
  type BusinessPliegoSectionKey,
} from '../constants/businessPliego'

import { PrimaryButton } from './PrimaryButton'

type BusinessPliegoFormProps = {
  sections: Record<BusinessPliegoSectionKey, string>
  onSectionChange: (key: BusinessPliegoSectionKey, value: string) => void
  onGenerate: (force: boolean) => Promise<void>
  onApprove: () => Promise<void>
  generateBusy: boolean
  approveBusy: boolean
  saveBusy: boolean
  onSave: () => Promise<void>
  approved: boolean
  generatedAt: string | null
  canApprove: boolean
  flowMsg: string | null
}

export function BusinessPliegoForm({
  sections,
  onSectionChange,
  onGenerate,
  onApprove,
  generateBusy,
  approveBusy,
  saveBusy,
  onSave,
  approved,
  generatedAt,
  canApprove,
  flowMsg,
}: BusinessPliegoFormProps) {
  return (
    <div className="space-y-4 rounded-md border border-black/10 bg-white p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-ink">Pliego de condiciones (secciones requeridas)</h3>
          <p className="text-xs text-muted">
            Genera un borrador autocompletado, revisa, guarda y aprueba antes de pasar a presupuesto.
            {generatedAt ? ` Borrador: ${new Date(generatedAt).toLocaleString()}.` : ''}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-md border border-primary/40 bg-primary/[0.08] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-primary hover:bg-primary/[0.12] disabled:opacity-50"
            disabled={generateBusy}
            onClick={() => void onGenerate(false)}
          >
            {generateBusy ? 'Generando…' : 'Generar borrador'}
          </button>
          <button
            type="button"
            className="rounded-md border border-black/15 bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-black/[0.03] disabled:opacity-50"
            disabled={generateBusy}
            onClick={() => {
              if (window.confirm('¿Regenerar? Se reemplaza el borrador y se anula un pliego aprobado previo al guardar.')) {
                void onGenerate(true)
              }
            }}
          >
            Regenerar
          </button>
          {canApprove ? (
            <PrimaryButton
              type="button"
              disabled={approveBusy || approved}
              onClick={() => void onApprove()}
            >
              {approved ? 'Aprobado' : approveBusy ? 'Aprobando…' : 'Aprobar pliego'}
            </PrimaryButton>
          ) : null}
        </div>
      </div>
      {approved ? (
        <p className="text-xs text-emerald-800">Pliego aprobado (editar requiere nueva aprobación).</p>
      ) : null}
      {flowMsg ? <p className="text-sm text-amber-900">{flowMsg}</p> : null}
      {BUSINESS_PLIEGO_SECTION_KEYS.map((key) => {
        const len = sections[key]?.trim().length ?? 0
        const short = len > 0 && len < MIN_PLIEGO_SECTION_LEN
        return (
          <div key={key} className="space-y-1">
            <label className="text-xs font-medium text-ink" htmlFor={`bp-${key}`}>
              {BUSINESS_PLIEGO_SECTION_LABELS[key]}
              <span className="text-muted"> — mín. {MIN_PLIEGO_SECTION_LEN} caracteres</span>
              {short ? <span className="ml-1 text-amber-700"> (corto)</span> : null}
            </label>
            <textarea
              id={`bp-${key}`}
              className="min-h-[88px] w-full rounded-md border border-black/15 p-2 text-sm text-ink"
              value={sections[key] ?? ''}
              onChange={(e) => onSectionChange(key, e.target.value)}
            />
          </div>
        )
      })}
      <div className="pt-1">
        <PrimaryButton type="button" disabled={saveBusy} onClick={() => void onSave()}>
          {saveBusy ? 'Guardando…' : 'Guardar secciones'}
        </PrimaryButton>
      </div>
    </div>
  )
}
