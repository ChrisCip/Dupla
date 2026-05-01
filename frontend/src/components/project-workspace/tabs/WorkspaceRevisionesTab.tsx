import { Card } from '../../Card'
import { PrimaryButton } from '../../PrimaryButton'
import type { RevisionRow } from '../../../types/projectWorkspace'

type WorkspaceRevisionesTabProps = {
  flowMsg: string | null
  revDecision: string
  setRevDecision: React.Dispatch<React.SetStateAction<string>>
  revNotes: string
  setRevNotes: React.Dispatch<React.SetStateAction<string>>
  revisions: RevisionRow[]
  onSubmitRevision: () => void
}

export function WorkspaceRevisionesTab({
  flowMsg,
  revDecision,
  setRevDecision,
  revNotes,
  setRevNotes,
  revisions,
  onSubmitRevision,
}: WorkspaceRevisionesTabProps) {
  return (
    <Card className="space-y-4 p-6">
      <h2 className="text-lg font-semibold text-ink">Revisiones de arquitectura</h2>
      <p className="text-sm text-muted">
        Puedes registrar revisiones cuando las necesites. Para pasar del paso de{' '}
        <span className="font-medium text-ink">revisión de arquitectura</span> al paso de{' '}
        <span className="font-medium text-ink">pliego de condiciones</span> en la plantilla de este proyecto, la última
        revisión debe estar <span className="font-medium text-ink">aprobada</span>.
      </p>
      {flowMsg ? <p className="text-sm text-primary">{flowMsg}</p> : null}
      <div className="space-y-3 border-b border-black/10 pb-4">
        <label className="block text-sm text-muted">
          Decisión
          <select className="du-input mt-1" value={revDecision} onChange={(e) => setRevDecision(e.target.value)}>
            <option value="APPROVED">APPROVED</option>
            <option value="REJECTED">REJECTED</option>
            <option value="PARTIAL">PARTIAL</option>
          </select>
        </label>
        <label className="block text-sm text-muted">
          Notas
          <textarea className="du-input mt-1 min-h-[80px]" value={revNotes} onChange={(e) => setRevNotes(e.target.value)} />
        </label>
        <PrimaryButton type="button" onClick={onSubmitRevision}>
          Registrar revisión
        </PrimaryButton>
      </div>
      <ul className="space-y-2 text-sm">
        {revisions.map((r) => (
          <li key={r.uuid} className="rounded border border-black/10 px-3 py-2">
            <span className="font-medium">v{r.version}</span> · {r.decision}
            {r.notes ? <p className="text-muted">{r.notes}</p> : null}
          </li>
        ))}
      </ul>
      {revisions.length === 0 ? <p className="text-sm text-muted">Sin revisiones.</p> : null}
    </Card>
  )
}
