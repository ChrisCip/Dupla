import { apiFetch } from '../../../api/client'
import { Card } from '../../Card'
import { PrimaryButton } from '../../PrimaryButton'
import type { SubcontractQuoteRow } from '../../../types/projectWorkspace'

type WorkspacePresupuestoTabProps = {
  projectUuid: string
  token: string | null
  flowMsg: string | null
  bpDraft: Record<string, unknown>
  setBpDraft: React.Dispatch<React.SetStateAction<Record<string, unknown>>>
  clientVersion: string
  setClientVersion: React.Dispatch<React.SetStateAction<string>>
  onSaveBudgetPipeline: () => void
  newQuoteTitle: string
  setNewQuoteTitle: React.Dispatch<React.SetStateAction<string>>
  activeQuote: string
  setActiveQuote: React.Dispatch<React.SetStateAction<string>>
  lineItem: string
  setLineItem: React.Dispatch<React.SetStateAction<string>>
  linePrice: string
  setLinePrice: React.Dispatch<React.SetStateAction<string>>
  quotes: SubcontractQuoteRow[]
  onLoadAuxLists: () => Promise<void>
}

export function WorkspacePresupuestoTab({
  projectUuid,
  token,
  flowMsg,
  bpDraft,
  setBpDraft,
  clientVersion,
  setClientVersion,
  onSaveBudgetPipeline,
  newQuoteTitle,
  setNewQuoteTitle,
  activeQuote,
  setActiveQuote,
  lineItem,
  setLineItem,
  linePrice,
  setLinePrice,
  quotes,
  onLoadAuxLists,
}: WorkspacePresupuestoTabProps) {
  return (
    <div className="space-y-6">
      <Card className="space-y-4 p-6">
        <h2 className="text-lg font-semibold text-ink">Pipeline de presupuesto</h2>
        <p className="text-sm text-muted">
          Esta fase sigue al <strong className="text-ink">pliego de condiciones</strong>. Marca cada hito cuando
          corresponda y registra la versión aprobada por el cliente antes del cierre.
        </p>
        {flowMsg ? <p className="text-sm text-primary">{flowMsg}</p> : null}
        {(
          [
            ['subcontracts_done', 'Cotizaciones de subcontratación listas'],
            ['volumetry_done', 'Volumetría completada'],
            ['cost_analysis_done', 'Análisis de costo completado'],
            ['budget_marked_complete', 'Presupuesto interno completado'],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!bpDraft[key]}
              onChange={(e) => setBpDraft((d) => ({ ...d, [key]: e.target.checked }))}
            />
            {label}
          </label>
        ))}
        <label className="block text-sm text-muted">
          Etiqueta de versión aprobada por el cliente
          <input
            className="du-input mt-1"
            value={clientVersion}
            onChange={(e) => setClientVersion(e.target.value)}
            placeholder="ej. v2"
          />
        </label>
        <PrimaryButton type="button" onClick={onSaveBudgetPipeline}>
          Guardar estado del pipeline
        </PrimaryButton>
      </Card>
      <Card className="space-y-4 p-6">
        <h3 className="text-md font-semibold text-ink">Cotizaciones</h3>
        <div className="flex flex-wrap gap-2">
          <input
            className="du-input flex-1 min-w-[160px]"
            placeholder="Título de cotización"
            value={newQuoteTitle}
            onChange={(e) => setNewQuoteTitle(e.target.value)}
          />
          <PrimaryButton
            type="button"
            onClick={async () => {
              if (!token) return
              const res = await apiFetch(`/api/projects/${projectUuid}/subcontracts`, {
                method: 'POST',
                token,
                body: JSON.stringify({ title: newQuoteTitle.trim() || null }),
              })
              if (res.ok) {
                setNewQuoteTitle('')
                await onLoadAuxLists()
              }
            }}
          >
            Nueva cotización
          </PrimaryButton>
        </div>
        <label className="block text-sm text-muted">
          Cotización activa para líneas
          <select className="du-input mt-1" value={activeQuote} onChange={(e) => setActiveQuote(e.target.value)}>
            <option value="">—</option>
            {quotes.map((q) => (
              <option key={q.uuid} value={q.uuid}>
                {q.title ?? q.uuid.slice(0, 8)}
              </option>
            ))}
          </select>
        </label>
        <div className="flex flex-wrap gap-2">
          <input
            className="du-input flex-1 min-w-[120px]"
            placeholder="Ítem"
            value={lineItem}
            onChange={(e) => setLineItem(e.target.value)}
          />
          <input
            className="du-input w-28"
            placeholder="Precio"
            type="number"
            value={linePrice}
            onChange={(e) => setLinePrice(e.target.value)}
          />
          <PrimaryButton
            type="button"
            disabled={!activeQuote}
            onClick={async () => {
              if (!token || !activeQuote) return
              const res = await apiFetch(`/api/projects/${projectUuid}/subcontracts/${activeQuote}/lines`, {
                method: 'POST',
                token,
                body: JSON.stringify({
                  item_label: lineItem.trim(),
                  price: Number(linePrice),
                  currency: 'MXN',
                }),
              })
              if (res.ok) {
                setLineItem('')
                setLinePrice('')
                await onLoadAuxLists()
              }
            }}
          >
            Agregar línea
          </PrimaryButton>
        </div>
        {quotes.map((q) => (
          <div key={q.uuid} className="rounded border border-black/5 p-3 text-sm">
            <div className="font-medium">{q.title ?? 'Sin título'}</div>
            <ul className="mt-2 list-disc pl-5 text-muted">
              {q.lines.map((l) => (
                <li key={l.uuid}>
                  {l.item_label} — {l.price} {l.currency}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </Card>
    </div>
  )
}
