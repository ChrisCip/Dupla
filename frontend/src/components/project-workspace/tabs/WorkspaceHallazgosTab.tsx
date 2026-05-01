import { useCallback, useState } from 'react'

import { apiFetch } from '../../../api/client'
import { Card } from '../../Card'
import { PrimaryButton } from '../../PrimaryButton'
import type { TechnicalFindingRow } from '../../../types/projectWorkspace'

const SEVERITY_OPTIONS = ['crítico', 'alto', 'medio', 'bajo'] as const

type WorkspaceHallazgosTabProps = {
  projectUuid: string
  token: string | null
  findings: TechnicalFindingRow[]
  onRefresh: () => Promise<void>
}

export function WorkspaceHallazgosTab({
  projectUuid,
  token,
  findings,
  onRefresh,
}: WorkspaceHallazgosTabProps) {
  const [discipline, setDiscipline] = useState('')
  const [severity, setSeverity] = useState<string>('medio')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [evidenceRef, setEvidenceRef] = useState('')
  const [submitBusy, setSubmitBusy] = useState(false)
  const [localErr, setLocalErr] = useState<string | null>(null)

  const submit = useCallback(async () => {
    if (!token || !discipline.trim() || !title.trim() || !description.trim()) return
    setSubmitBusy(true)
    setLocalErr(null)
    try {
      const body = {
        discipline: discipline.trim(),
        severity: severity.trim() || 'medio',
        title: title.trim(),
        description: description.trim(),
        evidence_ref: evidenceRef.trim() || null,
      }
      const res = await apiFetch(`/api/projects/${projectUuid}/technical-findings`, {
        method: 'POST',
        token,
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        setLocalErr((j as { detail?: string }).detail ?? 'No se pudo guardar el hallazgo')
        return
      }
      setTitle('')
      setDescription('')
      setEvidenceRef('')
      await onRefresh()
    } finally {
      setSubmitBusy(false)
    }
  }, [token, projectUuid, discipline, severity, title, description, evidenceRef, onRefresh])

  return (
    <div className="space-y-6">
      <Card className="space-y-4 p-6">
        <h2 className="text-lg font-semibold text-ink">Hallazgos técnicos</h2>
        <p className="text-sm text-muted">
          Registro manual de interferencias u observaciones (compatible con severidades para uso futuro con reglas /
          OCR).
        </p>
        {localErr ? <p className="text-sm text-primary">{localErr}</p> : null}
        <ul className="divide-y divide-black/10 border-y border-black/10">
          {findings.length === 0 ? (
            <li className="py-4 text-sm text-muted">Ningún hallazgo registrado todavía.</li>
          ) : (
            findings.map((f) => (
              <li key={f.uuid} className="py-3">
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="font-medium text-ink">{f.title}</span>
                  <span className="rounded bg-black/[0.06] px-1.5 py-0.5 text-xs font-medium text-muted">
                    {f.severity}
                  </span>
                  <span className="text-xs text-muted">{f.discipline}</span>
                </div>
                <p className="mt-1 text-sm text-ink">{f.description}</p>
                {f.evidence_ref ? (
                  <p className="mt-1 text-xs text-muted">Ref.: {f.evidence_ref}</p>
                ) : null}
                <p className="mt-1 text-xs text-muted">{new Date(f.created_at).toLocaleString()}</p>
              </li>
            ))
          )}
        </ul>
      </Card>

      <Card className="space-y-4 p-6">
        <h3 className="text-md font-semibold text-ink">Registrar hallazgo</h3>
        <label className="block text-sm text-muted">
          Disciplina
          <input
            className="du-input mt-1"
            value={discipline}
            onChange={(e) => setDiscipline(e.target.value)}
            placeholder="ej. arquitectura, instalaciones"
          />
        </label>
        <label className="block text-sm text-muted">
          Severidad
          <select
            className="du-input mt-1"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
          >
            {SEVERITY_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm text-muted">
          Título
          <input className="du-input mt-1" value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label className="block text-sm text-muted">
          Descripción
          <textarea
            className="du-input mt-1 min-h-[88px]"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <label className="block text-sm text-muted">
          Referencia de evidencia (opcional)
          <input
            className="du-input mt-1"
            value={evidenceRef}
            onChange={(e) => setEvidenceRef(e.target.value)}
            placeholder="Plan, folio o enlace interno"
          />
        </label>
        <PrimaryButton type="button" disabled={submitBusy || !token} onClick={() => void submit()}>
          {submitBusy ? 'Guardando…' : 'Guardar hallazgo'}
        </PrimaryButton>
      </Card>
    </div>
  )
}
