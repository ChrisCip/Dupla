import { Card } from '../../Card'
import { PrimaryButton } from '../../PrimaryButton'
import { PLAN_DELIVERY_STATUS_OPTIONS } from '../../../constants/planDeliveryStatus'
import type { PlanDeliveryRow } from '../../../types/planDelivery'

type WorkspaceEntregaPlanosTabProps = {
  projectUuid: string
  token: string | null
  projectName: string | undefined
  planDeliveryRows: PlanDeliveryRow[]
  planDeliveryMsg: string | null
  setPlanDeliveryRows: React.Dispatch<React.SetStateAction<PlanDeliveryRow[]>>
  onAddRow: () => void
  onPatchRow: (rowUuid: string, patch: Record<string, unknown>) => void
  onDeleteRow: (rowUuid: string) => void
}

export function WorkspaceEntregaPlanosTab({
  projectUuid,
  token,
  projectName,
  planDeliveryRows,
  planDeliveryMsg,
  setPlanDeliveryRows,
  onAddRow,
  onPatchRow,
  onDeleteRow,
}: WorkspaceEntregaPlanosTabProps) {
  return (
    <Card className="space-y-4 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-ink">Control entrega de planos</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Registro tipo GA-FO-03. Cada solicitud recibe un número <span className="font-mono">SDP NNNN</span> único en
            este proyecto. La columna «Cantidad días» muestra el valor registrado o la diferencia entre fechas de
            solicitud y entrega.
          </p>
        </div>
        <PrimaryButton type="button" disabled={!token || !projectUuid} onClick={onAddRow}>
          Nueva solicitud
        </PrimaryButton>
      </div>
      {planDeliveryMsg ? <p className="text-sm text-primary">{planDeliveryMsg}</p> : null}
      <div className="overflow-x-auto rounded border border-black/10">
        <table className="w-full min-w-[960px] text-left text-sm">
          <thead className="bg-black/[0.04] text-xs uppercase text-muted">
            <tr>
              <th className="px-3 py-2">No.</th>
              <th className="px-3 py-2">Fecha solicitud</th>
              <th className="px-3 py-2">Proyecto</th>
              <th className="px-3 py-2">No. solicitud</th>
              <th className="px-3 py-2">Descripción</th>
              <th className="px-3 py-2">Fecha entrega</th>
              <th className="px-3 py-2">Cant. días</th>
              <th className="px-3 py-2">Estado</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {planDeliveryRows.map((row, idx) => (
              <tr key={row.uuid} className="border-t border-black/5 odd:bg-black/[0.015]">
                <td className="px-3 py-2 align-top tabular-nums text-muted">{idx + 1}</td>
                <td className="px-3 py-2 align-top">
                  <input
                    type="date"
                    className="du-input w-[10.5rem] py-1.5 text-sm"
                    value={row.request_date ? row.request_date.slice(0, 10) : ''}
                    onChange={(e) => {
                      const v = e.target.value
                      void onPatchRow(row.uuid, {
                        request_date: v ? v : null,
                      })
                    }}
                    aria-label="Fecha de solicitud"
                  />
                </td>
                <td className="px-3 py-2 align-top text-sm text-ink">{projectName ?? '—'}</td>
                <td className="px-3 py-2 align-top font-mono text-xs text-ink">{row.request_number}</td>
                <td className="px-3 py-2 align-top">
                  <input
                    className="du-input min-w-[200px] py-1.5 text-sm"
                    value={row.description}
                    onChange={(e) => {
                      const v = e.target.value
                      setPlanDeliveryRows((prev) =>
                        prev.map((r) => (r.uuid === row.uuid ? { ...r, description: v } : r)),
                      )
                    }}
                    onBlur={(e) => {
                      const v = e.target.value.trim()
                      void onPatchRow(row.uuid, { description: v })
                    }}
                    aria-label="Descripción"
                  />
                </td>
                <td className="px-3 py-2 align-top">
                  <input
                    type="date"
                    className="du-input w-[10.5rem] py-1.5 text-sm"
                    value={row.delivery_date ? row.delivery_date.slice(0, 10) : ''}
                    onChange={(e) => {
                      const v = e.target.value
                      void onPatchRow(row.uuid, {
                        delivery_date: v ? v : null,
                      })
                    }}
                    aria-label="Fecha de entrega"
                  />
                </td>
                <td className="px-3 py-2 align-top">
                  <input
                    type="number"
                    min={0}
                    className="du-input w-20 py-1.5 text-sm"
                    placeholder="Auto"
                    defaultValue={row.days_count ?? ''}
                    key={`${row.uuid}-days-${row.updated_at}`}
                    onBlur={(e) => {
                      const raw = e.target.value.trim()
                      const n = raw === '' ? null : Number(raw)
                      void onPatchRow(row.uuid, {
                        days_count: n === null || Number.isNaN(n) ? null : n,
                      })
                    }}
                    aria-label="Cantidad de días"
                  />
                  {row.days_resolved != null ? (
                    <div className="du-meta mt-0.5">Calc: {row.days_resolved}</div>
                  ) : null}
                </td>
                <td className="px-3 py-2 align-top">
                  <select
                    className="du-input py-1.5 text-sm"
                    value={row.status}
                    onChange={(e) => void onPatchRow(row.uuid, { status: e.target.value })}
                    aria-label="Estado"
                  >
                    {PLAN_DELIVERY_STATUS_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2 align-top">
                  <button
                    type="button"
                    className="text-sm font-medium text-primary underline-offset-2 hover:underline"
                    onClick={() => void onDeleteRow(row.uuid)}
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {planDeliveryRows.length === 0 ? (
        <p className="text-sm text-muted">No hay solicitudes. Usa «Nueva solicitud» para crear la primera.</p>
      ) : null}
    </Card>
  )
}
