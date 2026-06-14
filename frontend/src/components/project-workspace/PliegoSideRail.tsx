import { Check, CheckSquare, GitBranch, Share2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { apiFetch } from '../../api/client'
import { gaFoSectionProgressRows } from '../../lib/pliegoFormState'
import type { PliegoItemState } from '../../types/pliegoForm'
import { PrimaryButton } from '../PrimaryButton'
import { PliegoProjectChatSnippet } from './PliegoProjectChatSnippet'

type PliegoSideRailProps = {
  projectUuid: string
  token: string | null
  userUuid: string | null
  itemStates: Record<string, PliegoItemState>
  approved: boolean
  generatedAt: string | null
  canApprove: boolean
  viewBudget: boolean
  approveBusy: boolean
  onApprove: () => Promise<void>
  onGoPresupuesto?: () => void
}

export function PliegoSideRail({
  projectUuid,
  token,
  userUuid,
  itemStates,
  approved,
  generatedAt,
  canApprove,
  viewBudget,
  approveBusy,
  onApprove,
  onGoPresupuesto,
}: PliegoSideRailProps) {
  const navigate = useNavigate()
  const rows = gaFoSectionProgressRows(itemStates)

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
        <p className="mt-1 text-[11px] leading-relaxed text-muted">
          Cada sección del GA-FO-01 debe tener todos sus documentos en Completo o No aplica antes de aprobar el pliego.
        </p>
        <ul className="mt-3 max-h-[min(52vh,28rem)] space-y-2 overflow-y-auto pr-0.5">
          {rows.map((row) => {
            const ok = row.done === row.total && row.total > 0
            return (
              <li
                key={row.id}
                className="flex items-start gap-3 rounded-lg border border-black/8 bg-black/[0.02] px-3 py-2.5 text-xs"
              >
                <span
                  className={`mt-0.5 flex size-[18px] shrink-0 items-center justify-center rounded border ${
                    ok ? 'border-primary bg-primary text-white' : 'border-black/18 bg-white'
                  }`}
                  aria-hidden
                >
                  {ok ? <Check className="size-3 stroke-[3]" aria-hidden /> : null}
                </span>
                <span className={`min-w-0 leading-snug ${ok ? 'text-muted' : 'text-ink'}`}>
                  <span className={`block font-semibold ${ok ? 'line-through' : ''}`}>{row.titulo}</span>
                  <span className="mt-0.5 block text-[10px] tabular-nums text-muted">
                    {row.done} de {row.total} documentos listos
                  </span>
                </span>
              </li>
            )
          })}
        </ul>
      </div>

      <PliegoProjectChatSnippet projectUuid={projectUuid} token={token} userUuid={userUuid} />

      <div className="rounded-xl border border-black/10 bg-white p-4 shadow-[var(--shadow-card)]">
        <p className="text-xs text-muted">
          Estado:{' '}
          <span className="font-semibold text-ink">{approved ? 'Aprobado' : 'Borrador / revisión'}</span>
        </p>
        <p className="mt-1 text-xs text-muted">
          Última marca de aprobación:{' '}
          <span className="font-mono text-ink">
            {generatedAt ? new Date(generatedAt).toLocaleString() : '—'}
          </span>
        </p>
        {canApprove ? (
          <PrimaryButton
            type="button"
            className="mt-4 w-full gap-2 py-3 text-sm font-semibold tracking-normal"
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
        {viewBudget ? (
          <button
            type="button"
            className="mt-2 flex w-full items-center justify-center gap-2 text-xs font-semibold text-primary underline-offset-2 hover:underline"
            onClick={() => onGoPresupuesto?.()}
          >
            <GitBranch className="size-3.5" strokeWidth={2} aria-hidden />
            Ver presupuesto maestro
          </button>
        ) : null}
      </div>
    </aside>
  )
}
