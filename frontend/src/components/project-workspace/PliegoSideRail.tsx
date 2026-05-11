import { Check, CheckSquare, GitBranch, Share2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { apiFetch } from '../../api/client'
import {
  BUSINESS_PLIEGO_SECTION_KEYS,
  BUSINESS_PLIEGO_SECTION_LABELS,
  MIN_PLIEGO_SECTION_LEN,
  type BusinessPliegoSectionKey,
} from '../../constants/businessPliego'
import { PrimaryButton } from '../PrimaryButton'
import { PliegoProjectChatSnippet } from './PliegoProjectChatSnippet'

type PliegoSideRailProps = {
  projectUuid: string
  token: string | null
  userUuid: string | null
  sections: Record<BusinessPliegoSectionKey, string>
  approved: boolean
  generatedAt: string | null
  canApprove: boolean
  approveBusy: boolean
  onApprove: () => Promise<void>
}

export function PliegoSideRail({
  projectUuid,
  token,
  userUuid,
  sections,
  approved,
  generatedAt,
  canApprove,
  approveBusy,
  onApprove,
}: PliegoSideRailProps) {
  const navigate = useNavigate()

  const sectionChecks = BUSINESS_PLIEGO_SECTION_KEYS.map((k) => ({
    key: k,
    label: BUSINESS_PLIEGO_SECTION_LABELS[k],
    ok: (sections[k]?.trim().length ?? 0) >= MIN_PLIEGO_SECTION_LEN,
  }))

  const doneCount = sectionChecks.filter((s) => s.ok).length

  async function openProjectChatNavigate() {
    if (!token) {
      navigate('/app/chat')
      return
    }
    const res = await apiFetch(`/api/projects/${projectUuid}/chat/conversation`, {
      method: 'POST',
      token,
    })
    if (!res.ok) {
      navigate('/app/chat')
      return
    }
    const j = (await res.json()) as { uuid?: string }
    if (j.uuid) {
      navigate(`/app/chat?conversation=${encodeURIComponent(j.uuid)}`)
      return
    }
    navigate('/app/chat')
  }

  return (
    <aside className="flex w-full shrink-0 flex-col gap-4 lg:w-[min(100%,22rem)] xl:w-96 print:hidden">
      <div className="rounded-xl border border-black/10 bg-white p-4 shadow-[var(--shadow-card)]">
        <div className="flex items-center gap-2 text-primary">
          <CheckSquare className="size-5 shrink-0" strokeWidth={2} aria-hidden />
          <h3 className="text-sm font-semibold uppercase tracking-wide text-ink">Lista de revisión</h3>
        </div>
        <p className="mt-1 text-[11px] text-muted">
          Progreso del documento técnico: cada bloque del acordeón debe superar el mínimo de caracteres antes de
          aprobar.
        </p>
        <p className="mt-2 text-xs font-semibold tabular-nums text-ink">
          {doneCount}/{sectionChecks.length} secciones listas
        </p>
        <ul className="mt-3 max-h-[min(52vh,28rem)] space-y-2 overflow-y-auto pr-1">
          {sectionChecks.map((s) => (
            <li key={s.key} className="flex items-start gap-2 text-xs">
              <span
                className={`mt-0.5 flex size-4 shrink-0 items-center justify-center rounded border ${
                  s.ok ? 'border-primary bg-primary text-white' : 'border-black/20 bg-white'
                }`}
                aria-hidden
              >
                {s.ok ? <Check className="size-3 stroke-[3]" aria-hidden /> : null}
              </span>
              <span className={`leading-snug ${s.ok ? 'text-muted line-through' : 'text-ink'}`}>{s.label}</span>
            </li>
          ))}
        </ul>
      </div>

      <PliegoProjectChatSnippet projectUuid={projectUuid} token={token} userUuid={userUuid} />

      <div className="rounded-xl border border-black/10 bg-white p-4 shadow-[var(--shadow-card)]">
        <p className="text-xs text-muted">
          Estado:{' '}
          <span className="font-semibold text-ink">{approved ? 'Aprobado' : 'Borrador / revisión'}</span>
        </p>
        <p className="mt-1 text-xs text-muted">
          Versión borrador:{' '}
          <span className="font-mono text-ink">
            {generatedAt ? new Date(generatedAt).toLocaleDateString() : '—'}
          </span>
        </p>
        {canApprove ? (
          <PrimaryButton
            type="button"
            className="mt-4 w-full gap-2 py-3 text-sm font-semibold normal-case tracking-normal"
            disabled={approveBusy || approved}
            onClick={() => void onApprove()}
          >
            <CheckSquare className="size-4" strokeWidth={2} aria-hidden />
            {approved ? 'Pliego aprobado' : approveBusy ? 'Aprobando…' : 'Aprobar pliego'}
          </PrimaryButton>
        ) : null}
        <button
          type="button"
          className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-black/15 bg-white py-3 text-sm font-semibold text-ink shadow-sm transition hover:bg-black/[0.03]"
          onClick={() => void openProjectChatNavigate()}
        >
          <Share2 className="size-4 text-primary" strokeWidth={2} aria-hidden />
          Solicitar cambios
        </button>
        <button
          type="button"
          className="mt-2 flex w-full items-center justify-center gap-2 text-xs font-semibold text-primary underline-offset-2 hover:underline"
          onClick={() => navigate(`/app/projects/${projectUuid}?tab=flujo`)}
        >
          <GitBranch className="size-3.5" strokeWidth={2} aria-hidden />
          Ver flujo del proyecto
        </button>
      </div>
    </aside>
  )
}
