import { useCallback, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import {
  addClashWorkflowComment,
  getClashWorkflowDashboard,
  getClashWorkflowDetail,
  getClashWorkflowFilters,
  listClashWorkflowRows,
  recordClashWorkflowDecision,
  requestClashReanalysis,
  updateClashWorkflowStatus,
  uploadClashCorrection,
} from '../../api/clashWorkflow'
import {
  DECISION_LABELS,
  DECISION_ORDER,
  PRIORITY_CLASSES,
  SEVERITY_CLASSES,
  STATUS_CLASSES,
  STATUS_LABELS,
  STATUS_TRANSITIONS,
} from '../../lib/clashWorkflowLabels'
import { incidentSubtitle, incidentTitle, severityDisplayLabel } from '../../lib/clashSeverity'
import type {
  ClashDetail,
  ClashFilters,
  ClashRow,
  ClashStatus,
  CorrectionTarget,
  DashboardMetrics,
  FilterOptions,
  Priority,
  Severity,
} from '../../types/clashWorkflow'
import { Card } from '../Card'
import { IncidentVisualPreview } from './IncidentVisualPreview'

const CORRECTION_TARGET_OPTIONS: { value: CorrectionTarget; label: string }[] = [
  { value: 'dwg_a', label: 'DWG A' },
  { value: 'dwg_b', label: 'DWG B' },
  { value: 'both', label: 'Ambos DWG' },
]

const CORRECTION_STATUSES: ClashStatus[] = [
  'correction_required',
  'correction_uploaded',
  'pending_reanalysis',
  'still_present',
]

function defaultCorrectionTarget(clash: ClashDetail): CorrectionTarget {
  switch (clash.reviewer_decision) {
    case 'correct_dwg_a':
      return 'dwg_a'
    case 'correct_dwg_b':
      return 'dwg_b'
    case 'correct_both':
      return 'both'
    default:
      return 'dwg_a'
  }
}

type Props = {
  projectUuid: string
  token: string | null
  visible: boolean
}

function Badge({ className, children }: { className: string; children: ReactNode }) {
  return (
    <span className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${className}`}>
      {children}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: Priority }) {
  return <Badge className={PRIORITY_CLASSES[priority]}>{priority}</Badge>
}

function SeverityBadge({ severity, label }: { severity: Severity; label: string }) {
  return <Badge className={SEVERITY_CLASSES[severity]}>{label}</Badge>
}

function planLabel(base: string | null | undefined, fallback: string | null | undefined): string {
  return base?.trim() || fallback?.trim() || '—'
}

function IncidentPlans({ clash }: { clash: ClashRow }) {
  const base = planLabel(clash.base_plan_number, clash.dwg_a)
  const compared = planLabel(clash.compared_plan_number, clash.dwg_b)
  return (
    <div className="grid grid-cols-2 gap-2">
      <div className="min-w-0 rounded-md border border-primary/20 bg-primary/[0.05] px-2 py-1.5">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-primary">Plano base</div>
        <div className="truncate text-xs font-medium text-ink">{base}</div>
      </div>
      <div className="min-w-0 rounded-md border border-black/15 bg-black/[0.03] px-2 py-1.5">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-muted">Plano comparado</div>
        <div className="truncate text-xs font-medium text-ink">{compared}</div>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: ClashStatus }) {
  return <Badge className={STATUS_CLASSES[status]}>{STATUS_LABELS[status]}</Badge>
}

function MetricCard({
  label,
  value,
  tone = 'default',
  onClick,
}: {
  label: string
  value: number
  tone?: 'default' | 'primary' | 'amber' | 'emerald'
  onClick?: () => void
}) {
  const tones = {
    default: 'border-black/10 bg-white',
    primary: 'border-primary/25 bg-primary/[0.06]',
    amber: 'border-amber-500/25 bg-amber-500/8',
    emerald: 'border-emerald-600/20 bg-emerald-600/8',
  }
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg border p-3 text-left transition hover:shadow-sm ${tones[tone]} ${
        onClick ? 'cursor-pointer' : 'cursor-default'
      }`}
    >
      <div className="text-2xl font-bold tabular-nums text-ink">{value}</div>
      <div className="mt-1 text-xs text-muted">{label}</div>
    </button>
  )
}

function IncidentVisualSection({ clash, token }: { clash: ClashDetail; token: string | null }) {
  const preview = clash.visual_preview
  return (
    <div className="space-y-2">
      <IncidentPlans clash={clash} />
      <IncidentVisualPreview
        token={token}
        composedFullPageUrl={preview?.composed_full_page_url}
        zoomUrl={preview?.zoom_url}
        hasRealVisual={preview?.has_real_visual}
        visualWarnings={preview?.visual_warnings}
        title={incidentTitle(clash)}
      />
    </div>
  )
}

function CorrectionSection({
  projectUuid,
  token,
  clash,
  onChanged,
}: {
  projectUuid: string
  token: string | null
  clash: ClashDetail
  onChanged: () => void
}) {
  const [target, setTarget] = useState<CorrectionTarget>(() => defaultCorrectionTarget(clash))
  const [revision, setRevision] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasUnresolvedCorrection = clash.corrections.some((c) => !c.result)
  const canReanalyze =
    hasUnresolvedCorrection &&
    (clash.status === 'correction_uploaded' || clash.status === 'pending_reanalysis')

  const upload = async () => {
    if (!token || !file) return
    setBusy(true)
    setError(null)
    try {
      await uploadClashCorrection(projectUuid, token, clash.id, {
        target,
        revisionName: revision.trim() || file.name,
        file,
      })
      setFile(null)
      setRevision('')
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo subir la corrección')
    } finally {
      setBusy(false)
    }
  }

  const reanalyze = async (outcome: 'resolved' | 'still_present') => {
    if (!token) return
    setBusy(true)
    setError(null)
    try {
      await requestClashReanalysis(projectUuid, token, clash.id, outcome)
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo reanalizar')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded-lg border border-orange-500/25 bg-orange-500/[0.05] p-3">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-orange-900">
        Resubida de corrección
      </h4>
      <p className="mt-1 text-xs text-muted">
        El DWG corregido se guarda como revisión nueva; el original nunca se sobrescribe.
      </p>
      {error ? <p className="mt-2 text-xs text-primary">{error}</p> : null}

      {clash.corrections.length > 0 ? (
        <ul className="mt-2 space-y-1">
          {clash.corrections.map((c) => (
            <li key={c.id} className="rounded border border-black/10 bg-white px-2 py-1 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-ink">{c.revision_name}</span>
                <span className="text-muted">{c.target_label}</span>
              </div>
              <div className="text-muted">
                {c.file_name} · {c.uploaded_by}
                {c.result_label ? ` · ${c.result_label}` : ' · sin reanalizar'}
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="mt-3 space-y-2">
        <select
          className="du-input w-full text-sm"
          value={target}
          onChange={(e) => setTarget(e.target.value as CorrectionTarget)}
          disabled={busy}
        >
          {CORRECTION_TARGET_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              Corregir {o.label}
            </option>
          ))}
        </select>
        <input
          className="du-input w-full text-sm"
          placeholder="Nombre de revisión (ej. R02)"
          value={revision}
          onChange={(e) => setRevision(e.target.value)}
          disabled={busy}
        />
        <input
          type="file"
          accept=".dwg,.dxf"
          className="block w-full text-xs text-muted file:mr-2 file:rounded file:border-0 file:bg-primary/10 file:px-2 file:py-1 file:text-primary"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          disabled={busy}
        />
        <button
          type="button"
          disabled={busy || !file || !token}
          onClick={() => void upload()}
          className="du-pill-action w-full justify-center text-xs disabled:opacity-50"
        >
          {busy ? 'Procesando…' : 'Subir DWG corregido'}
        </button>
      </div>

      {canReanalyze ? (
        <div className="mt-3 border-t border-orange-500/20 pt-3">
          <p className="text-xs font-medium text-ink">Reanalizar el par corregido</p>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              disabled={busy || !token}
              onClick={() => void reanalyze('resolved')}
              className="flex-1 rounded-md border border-emerald-600/30 bg-emerald-600/10 px-2 py-1.5 text-xs font-medium text-emerald-900 disabled:opacity-50"
            >
              Clash resuelto
            </button>
            <button
              type="button"
              disabled={busy || !token}
              onClick={() => void reanalyze('still_present')}
              className="flex-1 rounded-md border border-primary/30 bg-primary/10 px-2 py-1.5 text-xs font-medium text-primary disabled:opacity-50"
            >
              Persiste
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function ClashDetailPanel({
  projectUuid,
  token,
  itemId,
  onClose,
  onChanged,
}: {
  projectUuid: string
  token: string | null
  itemId: string
  onClose: () => void
  onChanged: () => void
}) {
  const [clash, setClash] = useState<ClashDetail | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [comment, setComment] = useState('')

  const load = useCallback(() => {
    if (!token) return
    void getClashWorkflowDetail(projectUuid, token, itemId).then(setClash)
  }, [projectUuid, token, itemId])

  useEffect(() => {
    load()
  }, [load])

  const run = async (fn: () => Promise<boolean>) => {
    setBusy(true)
    setError(null)
    try {
      const ok = await fn()
      if (!ok) setError('No se pudo guardar el cambio')
      else {
        load()
        onChanged()
      }
    } finally {
      setBusy(false)
    }
  }

  if (!clash) {
    return (
      <aside className="w-full shrink-0 border-l border-black/10 bg-white p-4 lg:w-[420px]">
        <p className="text-sm text-muted">Cargando detalle…</p>
      </aside>
    )
  }

  const transitions = STATUS_TRANSITIONS[clash.status]

  return (
    <aside className="sticky top-4 max-h-[calc(100vh-8rem)] w-full shrink-0 overflow-y-auto border-l border-black/10 bg-white lg:w-[420px]">
      <div className="flex items-start justify-between p-4 pb-0">
        <div className="min-w-0 flex-1">
          <h4 className="text-sm font-semibold leading-snug text-ink break-words">{incidentTitle(clash)}</h4>
          {incidentSubtitle(clash) ? (
            <p className="mt-1 text-xs text-muted break-words">{incidentSubtitle(clash)}</p>
          ) : null}
          <p className="mt-1 font-mono text-[10px] text-muted">{clash.clash_code}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <PriorityBadge priority={clash.priority} />
            <SeverityBadge severity={clash.severity} label={severityDisplayLabel(clash)} />
            <StatusBadge status={clash.status} />
          </div>
        </div>
        <button type="button" onClick={onClose} className="text-xl leading-none text-muted hover:text-ink">
          ×
        </button>
      </div>
      <div className="space-y-4 p-4">
        {error ? <p className="text-sm text-primary">{error}</p> : null}
        <IncidentVisualSection clash={clash} token={token} />
        {clash.table_comment?.trim() ? (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted">Observación</h4>
            <p className="mt-1 text-sm text-ink break-words whitespace-pre-wrap">{clash.table_comment}</p>
          </div>
        ) : null}
        {clash.recommended_action?.trim() ? (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted">Acción sugerida</h4>
            <p className="mt-1 text-sm text-ink break-words">{clash.recommended_action}</p>
          </div>
        ) : null}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted">Decisión del revisor</h4>
          <p className="mt-1 text-sm text-ink">
            {clash.reviewer_decision ? DECISION_LABELS[clash.reviewer_decision] : 'Sin decisión'}
          </p>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {DECISION_ORDER.map((d) => (
              <button
                key={d}
                type="button"
                disabled={busy || !token}
                onClick={() =>
                  void run(() => recordClashWorkflowDecision(projectUuid, token, itemId, d))
                }
                className={`rounded-md border px-2 py-1.5 text-left text-xs ${
                  clash.reviewer_decision === d
                    ? 'border-primary bg-primary text-white'
                    : 'border-black/15 hover:bg-black/[0.03]'
                }`}
              >
                {DECISION_LABELS[d]}
              </button>
            ))}
          </div>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted">Cambio de estado</h4>
          <div className="mt-2 flex flex-wrap gap-2">
            {transitions.map((s) => (
              <button
                key={s}
                type="button"
                disabled={busy || !token}
                onClick={() => void run(() => updateClashWorkflowStatus(projectUuid, token, itemId, s))}
                className="rounded-md border border-black/15 px-2 py-1 text-xs hover:bg-black/[0.03]"
              >
                → {STATUS_LABELS[s]}
              </button>
            ))}
          </div>
        </div>
        {CORRECTION_STATUSES.includes(clash.status) ? (
          <CorrectionSection
            projectUuid={projectUuid}
            token={token}
            clash={clash}
            onChanged={() => {
              load()
              onChanged()
            }}
          />
        ) : null}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted">Comando AutoCAD</h4>
          <div className="mt-1 rounded-md bg-ink px-3 py-2 font-mono text-xs text-white">
            {clash.location.autocad_zoom_window_command}
          </div>
        </div>
        <div className="flex gap-2">
          <input
            className="du-input flex-1 text-sm"
            placeholder="Comentario…"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <button
            type="button"
            disabled={busy || !comment.trim() || !token}
            onClick={() =>
              void run(async () => {
                const ok = await addClashWorkflowComment(projectUuid, token, itemId, comment.trim())
                if (ok) setComment('')
                return ok
              })
            }
            className="du-pill-action text-xs"
          >
            Enviar
          </button>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted">Bitácora</h4>
          <ol className="mt-2 space-y-2">
            {clash.audit_trail.map((e) => (
              <li key={e.id} className="border-l-2 border-primary/20 pl-2 text-xs">
                <div className="text-muted">
                  {e.created_at ? new Date(e.created_at).toLocaleString() : '—'} · {e.actor}
                </div>
                <div className="text-ink">{e.event_type}</div>
                {e.comment ? <div className="italic text-muted">{e.comment}</div> : null}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </aside>
  )
}

export function ClashWorkflowPanel({ projectUuid, token, visible }: Props) {
  const [filters, setFilters] = useState<ClashFilters>({})
  const [options, setOptions] = useState<FilterOptions | null>(null)
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [rows, setRows] = useState<ClashRow[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    if (!token || !visible) return
    setLoading(true)
    void (async () => {
      try {
        const [m, r] = await Promise.all([
          getClashWorkflowDashboard(projectUuid, token, filters),
          listClashWorkflowRows(projectUuid, token, filters),
        ])
        setMetrics(m)
        setRows(r)
        setError(null)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Error al cargar workflow')
      } finally {
        setLoading(false)
      }
    })()
  }, [token, visible, projectUuid, filters])

  useEffect(() => {
    if (!token || !visible) return
    void getClashWorkflowFilters(projectUuid, token).then(setOptions)
  }, [token, visible, projectUuid])

  useEffect(() => {
    load()
  }, [load])

  if (!visible) return null

  const applyFilter = (patch: ClashFilters) => {
    setFilters((prev) => {
      const next = { ...prev, ...patch }
      for (const k of Object.keys(next) as (keyof ClashFilters)[]) {
        if (!next[k]) delete next[k]
      }
      return next
    })
  }

  return (
    <section className="space-y-4 border-t border-black/10 pt-8" aria-labelledby="clash-workflow-heading">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id="clash-workflow-heading" className="text-lg font-semibold text-ink">
          Coordinación en vivo
        </h3>
        <span className="text-xs text-muted">Dashboard y tabla de clashes fusionados</span>
      </div>

      {error ? <p className="text-sm text-primary">{error}</p> : null}

      {metrics ? (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <MetricCard label="Total de clashes" value={metrics.total_clashes} onClick={() => setFilters({})} />
            <MetricCard
              label="Crítica"
              value={metrics.by_severity.critical}
              tone="primary"
              onClick={() => applyFilter({ severity: 'critical' })}
            />
            <MetricCard
              label="Alta"
              value={metrics.by_severity.high}
              tone="amber"
              onClick={() => applyFilter({ severity: 'high' })}
            />
            <MetricCard
              label="Media"
              value={metrics.by_severity.medium}
              onClick={() => applyFilter({ severity: 'medium' })}
            />
            <MetricCard
              label="Baja"
              value={metrics.by_severity.low}
              onClick={() => applyFilter({ severity: 'low' })}
            />
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
            <MetricCard
              label="Decisiones pendientes"
              value={metrics.pending_reviewer_decisions}
              tone="primary"
              onClick={() => applyFilter({ status: 'needs_review' })}
            />
            <MetricCard label="Resueltos" value={metrics.resolved} tone="emerald" onClick={() => applyFilter({ status: 'resolved' })} />
            <MetricCard
              label="Falsos positivos"
              value={metrics.false_positives}
              onClick={() => applyFilter({ status: 'false_positive' })}
            />
            <MetricCard
              label="Corrección cargada"
              value={metrics.correction_uploaded}
              onClick={() => applyFilter({ status: 'correction_uploaded' })}
            />
            <MetricCard
              label="Pendiente reanálisis"
              value={metrics.pending_reanalysis}
              onClick={() => applyFilter({ status: 'pending_reanalysis' })}
            />
            <MetricCard
              label="Persisten"
              value={metrics.still_present_after_reanalysis}
              tone="primary"
              onClick={() => applyFilter({ status: 'still_present' })}
            />
          </div>
        </>
      ) : null}

      <Card className="flex flex-wrap gap-3 p-3">
        <select
          className="du-input text-sm"
          value={filters.severity ?? ''}
          onChange={(e) => applyFilter({ severity: e.target.value || undefined })}
        >
          <option value="">Severidad</option>
          {options?.severities.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          className="du-input text-sm"
          value={filters.status ?? ''}
          onChange={(e) => applyFilter({ status: e.target.value || undefined })}
        >
          <option value="">Estado</option>
          {options?.statuses.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
        <select
          className="du-input text-sm"
          value={filters.level_id ?? ''}
          onChange={(e) => applyFilter({ level_id: e.target.value || undefined })}
        >
          <option value="">Nivel</option>
          {options?.levels.map((l) => (
            <option key={l} value={l}>
              {l}
            </option>
          ))}
        </select>
        <input
          className="du-input min-w-[140px] flex-1 text-sm"
          placeholder="Buscar DWG / capa"
          value={filters.dwg ?? ''}
          onChange={(e) => applyFilter({ dwg: e.target.value || undefined })}
        />
        <button type="button" className="du-pill-action text-sm" onClick={() => setFilters({})}>
          Limpiar filtros
        </button>
      </Card>

      <div className="flex items-start gap-4">
        <div className="min-w-0 flex-1 overflow-x-auto rounded-xl border border-black/10 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-black/10 text-left text-xs font-semibold uppercase tracking-wide text-muted">
                <th className="px-3 py-2">Incidencia</th>
                <th className="px-3 py-2">Subtítulo</th>
                <th className="px-3 py-2">Prio</th>
                <th className="px-3 py-2">Sev</th>
                <th className="px-3 py-2">Estado</th>
                <th className="px-3 py-2">DWG A</th>
                <th className="px-3 py-2">DWG B</th>
                <th className="px-3 py-2">Nivel</th>
                <th className="px-3 py-2">Capas</th>
                <th className="px-3 py-2">Responsable</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => setSelected(r.id)}
                  className={`cursor-pointer border-b border-black/[0.06] hover:bg-primary/[0.04] ${
                    selected === r.id ? 'bg-primary/[0.08]' : ''
                  }`}
                >
                  <td className="max-w-[200px] px-3 py-2">
                    <div className="truncate text-xs font-medium text-ink" title={incidentTitle(r)}>
                      {incidentTitle(r)}
                    </div>
                    <div className="truncate font-mono text-[10px] text-muted">{r.clash_code}</div>
                  </td>
                  <td className="max-w-[140px] truncate px-3 py-2 text-xs text-muted" title={r.short_label ?? ''}>
                    {incidentSubtitle(r) ?? '—'}
                  </td>
                  <td className="px-3 py-2">
                    <PriorityBadge priority={r.priority} />
                  </td>
                  <td className="px-3 py-2">
                    <SeverityBadge severity={r.severity} label={severityDisplayLabel(r)} />
                  </td>
                  <td className="px-3 py-2">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="max-w-[140px] truncate px-3 py-2" title={r.dwg_a ?? ''}>
                    {r.dwg_a}
                  </td>
                  <td className="max-w-[140px] truncate px-3 py-2" title={r.dwg_b ?? ''}>
                    {r.dwg_b}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{r.level_id}</td>
                  <td className="max-w-[120px] truncate px-3 py-2">{r.layers_involved}</td>
                  <td className="px-3 py-2">{r.assigned_to ?? '—'}</td>
                </tr>
              ))}
              {!loading && rows.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-3 py-8 text-center text-muted">
                    No hay clashes para estos filtros.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        {selected ? (
          <ClashDetailPanel
            projectUuid={projectUuid}
            token={token}
            itemId={selected}
            onClose={() => setSelected(null)}
            onChanged={load}
          />
        ) : null}
      </div>
    </section>
  )
}
