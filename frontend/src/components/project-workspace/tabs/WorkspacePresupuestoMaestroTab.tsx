import { Plus, RefreshCw } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import {
  aiSavingsHintDop,
  cloneBudgetRows,
  DEFAULT_LIQUIDACION_RATES,
  directSubtotalDop,
  lineTotalDop,
  lineTotalUsd,
  randomizeBudgetRows,
  rollExecutionScenarios,
  SECTION_FILTER_LABELS,
  seedBudgetRowsForProject,
  type DemoBudgetRow,
} from '../../../lib/projectMasterBudgetDemo'
import type { Project } from '../../../types/project'
import { PrimaryButton } from '../../PrimaryButton'

function fmtDop(n: number): string {
  return new Intl.NumberFormat('es-DO', {
    style: 'currency',
    currency: 'DOP',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

function fmtUsd(n: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

function fmtQty(q: number | null): string {
  if (q == null) return ''
  return new Intl.NumberFormat('es-DO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(q)
}

function computeLiquidacion(direct: number, rates = DEFAULT_LIQUIDACION_RATES) {
  const seguro = direct * (rates.seguroPct / 100)
  const gastosAdmin = direct * (rates.gastosAdminPct / 100)
  const transporte = direct * (rates.transportePct / 100)
  const direccion = direct * (rates.direccionTecnicaPct / 100)
  const subAntesItbis = direct + seguro + gastosAdmin + transporte + direccion
  const itbis = subAntesItbis * (rates.itbisPct / 100)
  const total = subAntesItbis + itbis
  return {
    seguro,
    gastosAdmin,
    transporte,
    direccion,
    subAntesItbis,
    itbis,
    total,
  }
}

type WorkspacePresupuestoMaestroTabProps = {
  project: Project | null
}

export function WorkspacePresupuestoMaestroTab({ project }: WorkspacePresupuestoMaestroTabProps) {
  const [rows, setRows] = useState<DemoBudgetRow[]>(() => seedBudgetRowsForProject(''))
  const [filterKey, setFilterKey] = useState<string>('all')

  useEffect(() => {
    const name = project?.name?.trim() ?? ''
    setRows(seedBudgetRowsForProject(name || 'Proyecto'))
  }, [project?.name])

  const filteredRows = useMemo(() => {
    if (filterKey === 'all') return rows
    return rows.filter((r) => r.sectionKey === filterKey)
  }, [rows, filterKey])

  const direct = useMemo(() => directSubtotalDop(rows), [rows])

  const scenarios = useMemo(() => rollExecutionScenarios(direct), [direct])

  const liq = useMemo(() => computeLiquidacion(direct), [direct])

  const [aiHintDop, setAiHintDop] = useState(0)
  useEffect(() => {
    setAiHintDop(aiSavingsHintDop(direct))
  }, [direct])

  function recalculate() {
    setRows((prev) => randomizeBudgetRows(cloneBudgetRows(prev)))
  }

  function addPartida() {
    const lastSection = [...rows].reverse().find((r) => r.kind === 'section')
    const sk = lastSection?.sectionKey ?? 'arq'
    const id = `new-${Date.now()}`
    const unitDop = 1500 + Math.round(Math.random() * 4000)
    const unitUsd = Math.round((unitDop / 56.85) * 10000) / 10000
    setRows((prev) => [
      ...prev,
      {
        id,
        sectionKey: sk,
        kind: 'item',
        code: 'NV',
        description: 'Nueva partida (editar en futura versión)',
        qty: 1,
        unit: 'ud',
        unitDop,
        unitUsd,
      },
    ])
  }

  const issueDate = useMemo(() => {
    const raw = project?.updated_at
    if (!raw) return new Date()
    const d = new Date(raw)
    return Number.isNaN(d.getTime()) ? new Date() : d
  }, [project?.updated_at])

  const location = project?.location_text?.trim() || 'República Dominicana'

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-6 pb-10">
      <nav className="flex flex-wrap gap-2 border-b border-black/10 pb-3 text-xs font-bold uppercase tracking-wide text-muted">
        <span className="border-b-2 border-primary pb-2 text-primary">Takeoff</span>
        <button type="button" disabled className="cursor-not-allowed pb-2 opacity-45">
          Cotizaciones
        </button>
        <button type="button" disabled className="cursor-not-allowed pb-2 opacity-45">
          Comparación
        </button>
        <button type="button" disabled className="cursor-not-allowed pb-2 opacity-45">
          Escenarios
        </button>
      </nav>

      <div className="rounded-xl border border-black/10 bg-white p-5 shadow-[var(--shadow-card)] sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 space-y-1">
            <p className="text-[11px] font-bold uppercase tracking-wide text-primary">Grupo Dupla</p>
            <h2 className="text-xl font-bold tracking-tight text-ink md:text-2xl">Presupuesto maestro</h2>
            <p className="text-sm text-muted">
              <span className="font-semibold text-ink">{project?.name ?? 'Obra'}</span>
              {project?.project_code ? (
                <span className="font-mono text-muted"> · {project.project_code}</span>
              ) : null}
            </p>
            <p className="text-xs text-muted">
              Ubicación: {location} · Emisión:{' '}
              {issueDate.toLocaleDateString('es-DO', { day: 'numeric', month: 'long', year: 'numeric' })}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <button
              type="button"
              disabled
              className="rounded-lg border border-black/15 bg-white px-4 py-2 text-xs font-semibold text-muted opacity-60"
              title="Próximamente — exportación PDF"
            >
              Exportar PDF
            </button>
            <PrimaryButton type="button" className="gap-1.5 px-4 py-2 text-xs font-bold normal-case" onClick={addPartida}>
              <Plus className="size-4" strokeWidth={2.5} aria-hidden />
              Nueva partida
            </PrimaryButton>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-primary/40 bg-primary/[0.08] px-4 py-2 text-xs font-bold text-primary hover:bg-primary/[0.12]"
              onClick={recalculate}
              title="Mock: aleatoriza cantidades y precios. Sustituir por llamada a API."
            >
              <RefreshCw className="size-4" strokeWidth={2} aria-hidden />
              Recalcular
            </button>
          </div>
        </div>

        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <label className="flex flex-wrap items-center gap-2 text-sm text-muted">
            <span className="text-[11px] font-bold uppercase tracking-wide">Filtrar por</span>
            <select
              className="du-input max-w-xs py-2 text-sm"
              value={filterKey}
              onChange={(e) => setFilterKey(e.target.value)}
            >
              {Object.entries(SECTION_FILTER_LABELS).map(([k, lab]) => (
                <option key={k} value={k}>
                  {lab}
                </option>
              ))}
            </select>
          </label>
          <p className="text-xs text-muted">
            Columnas en RD$ y USD referencial (TC demo). Liquidación e ITBIS son ilustrativos.
          </p>
        </div>

        <div className="mt-4 overflow-x-auto rounded-lg border border-black/10">
          <table className="w-full min-w-[920px] border-collapse text-left text-sm">
            <thead className="border-b border-black/10 bg-[#f8f9fb] text-[11px] font-bold uppercase tracking-wide text-muted">
              <tr>
                <th className="px-3 py-3">Num</th>
                <th className="min-w-[220px] px-3 py-3">Partida</th>
                <th className="px-3 py-3">Cantidad / UD</th>
                <th className="px-3 py-3">P/UD (RD$)</th>
                <th className="px-3 py-3">P/UD (USD)</th>
                <th className="px-3 py-3 text-right">Total RD$</th>
                <th className="px-3 py-3 text-right">Total USD</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((r) => {
                if (r.kind === 'section') {
                  return (
                    <tr key={r.id} className="border-b border-black/10 bg-black/[0.03]">
                      <td colSpan={7} className="px-3 py-2.5 text-xs font-bold uppercase tracking-wide text-ink">
                        {r.code} {r.description}
                      </td>
                    </tr>
                  )
                }
                const td = lineTotalDop(r)
                const tu = lineTotalUsd(r)
                return (
                  <tr key={r.id} className="border-b border-black/[0.06] hover:bg-black/[0.015]">
                    <td className="whitespace-nowrap px-3 py-2.5 font-mono text-xs text-muted">{r.code}</td>
                    <td className="px-3 py-2.5 font-medium text-ink">{r.description}</td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-muted">
                      {fmtQty(r.qty)} {r.unit ? <span className="text-ink">{r.unit}</span> : null}
                    </td>
                    <td className={`whitespace-nowrap px-3 py-2.5 tabular-nums ${r.kind === 'discount' ? 'text-primary' : ''}`}>
                      {fmtDop(r.unitDop)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 tabular-nums text-muted">{fmtUsd(r.unitUsd)}</td>
                    <td
                      className={`whitespace-nowrap px-3 py-2.5 text-right tabular-nums font-semibold ${td < 0 ? 'text-primary' : 'text-ink'}`}
                    >
                      {fmtDop(td)}
                    </td>
                    <td className={`whitespace-nowrap px-3 py-2.5 text-right tabular-nums ${tu < 0 ? 'text-primary' : 'text-muted'}`}>
                      {fmtUsd(tu)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex flex-col items-end gap-2 border-t border-black/10 pt-4">
          <p className="text-[11px] font-bold uppercase tracking-wide text-muted">Subtotal directo</p>
          <p className="text-3xl font-bold tabular-nums text-primary">{fmtDop(direct)}</p>
        </div>
      </div>

      <div>
        <h3 className="text-sm font-bold uppercase tracking-wide text-muted">Escenarios de ejecución</h3>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          {scenarios.map((s) => (
            <div
              key={s.id}
              className={`relative overflow-hidden rounded-xl border bg-white p-4 shadow-sm ${
                s.recommended ? 'border-primary ring-2 ring-primary/20' : 'border-black/10'
              }`}
            >
              {s.recommended ? (
                <span className="absolute right-0 top-0 rounded-bl-lg bg-primary px-2 py-1 text-[10px] font-bold uppercase text-white">
                  Recomendado
                </span>
              ) : null}
              <p className="text-xs font-bold uppercase tracking-wide text-muted">{s.title}</p>
              <p className="mt-2 text-xl font-bold tabular-nums text-ink">{fmtDop(s.totalDop)}</p>
              <p className={`mt-1 text-xs font-semibold ${s.pctVsBase >= 0 ? 'text-primary' : 'text-emerald-700'}`}>
                {s.pctVsBase >= 0 ? '+' : ''}
                {s.pctVsBase}% vs base
              </p>
              <p className="mt-2 text-xs leading-relaxed text-muted">{s.tagline}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-black/10 bg-[#f4f5f7] p-5 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-wide text-muted">Distribución de costos</p>
          <p className="mt-2 text-sm font-semibold text-ink">Análisis geográfico</p>
          <div className="mt-4 flex aspect-[21/10] items-center justify-center rounded-lg border border-dashed border-black/15 bg-linear-to-br from-black/10 via-black/5 to-primary/15 text-center text-xs text-muted">
            Mapa térmico / volumetría — conectar con datos de obra en una siguiente iteración.
          </div>
        </div>

        <div className="relative flex flex-col justify-between rounded-xl border border-primary/40 bg-primary p-5 text-white shadow-md">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-white/90">Optimización IA</p>
            <p className="mt-3 text-sm leading-relaxed text-white/95">
              Se detectó posible solapamiento entre partidas de acabados y créditos declarados. Recalcular ajusta el
              modelo local (mock) hasta integrar la API de consistencia presupuestaria.
            </p>
            <p className="mt-3 text-lg font-bold tabular-nums">
              Ahorro potencial estimado {fmtDop(aiHintDop)}
            </p>
          </div>
          <button
            type="button"
            className="mt-5 w-full rounded-lg bg-white py-2.5 text-sm font-bold text-primary shadow-sm hover:bg-white/95"
            onClick={recalculate}
          >
            Aplicar mejora (recalcular)
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-black/10 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-bold uppercase tracking-wide text-muted">Liquidación / indirectos / ITBIS</h3>
        <div className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
          <div className="flex justify-between gap-4 border-b border-black/8 py-2">
            <span className="text-muted">Costos directos</span>
            <span className="font-semibold tabular-nums text-ink">{fmtDop(direct)}</span>
          </div>
          <div className="flex justify-between gap-4 border-b border-black/8 py-2">
            <span className="text-muted">Seguro ({DEFAULT_LIQUIDACION_RATES.seguroPct}%)</span>
            <span className="tabular-nums text-ink">{fmtDop(liq.seguro)}</span>
          </div>
          <div className="flex justify-between gap-4 border-b border-black/8 py-2">
            <span className="text-muted">Gastos administrativos ({DEFAULT_LIQUIDACION_RATES.gastosAdminPct}%)</span>
            <span className="tabular-nums text-ink">{fmtDop(liq.gastosAdmin)}</span>
          </div>
          <div className="flex justify-between gap-4 border-b border-black/8 py-2">
            <span className="text-muted">Transporte ({DEFAULT_LIQUIDACION_RATES.transportePct}%)</span>
            <span className="tabular-nums text-ink">{fmtDop(liq.transporte)}</span>
          </div>
          <div className="flex justify-between gap-4 border-b border-black/8 py-2">
            <span className="text-muted">Dirección técnica ({DEFAULT_LIQUIDACION_RATES.direccionTecnicaPct}%)</span>
            <span className="tabular-nums text-ink">{fmtDop(liq.direccion)}</span>
          </div>
          <div className="flex justify-between gap-4 border-b border-black/8 py-2">
            <span className="text-muted">Subtotal antes ITBIS</span>
            <span className="font-medium tabular-nums text-ink">{fmtDop(liq.subAntesItbis)}</span>
          </div>
          <div className="flex justify-between gap-4 border-b border-black/8 py-2">
            <span className="text-muted">ITBIS ({DEFAULT_LIQUIDACION_RATES.itbisPct}%)</span>
            <span className="tabular-nums text-ink">{fmtDop(liq.itbis)}</span>
          </div>
          <div className="flex justify-between gap-4 py-2 sm:col-span-2">
            <span className="font-bold text-ink">Total general estimado</span>
            <span className="text-lg font-bold tabular-nums text-primary">{fmtDop(liq.total)}</span>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-amber-500/25 bg-amber-500/[0.06] p-5">
        <h3 className="text-sm font-bold uppercase tracking-wide text-amber-900">Observaciones</h3>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-relaxed text-ink">
          <li>
            Partidas marcadas como pendientes de definición final deben cerrarse antes de la versión para cliente (
            <strong className="font-semibold">pileta · upgrades de carpintería</strong>).
          </li>
          <li>Los descuentos reflejan créditos explícitos frente a presupuestos previos; validar con contrato marco.</li>
          <li>ITBIS y porcentajes indirectos son referenciales según lineamientos internos; ajustar a normativa vigente.</li>
        </ul>
      </div>
    </div>
  )
}
