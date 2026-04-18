import { PliegoCondicionesForm } from '../../PliegoCondicionesForm'
import type { PliegoItemState } from '../../../types/pliegoForm'

type WorkspaceEspecificacionesTabProps = {
  projectUuid: string
  token: string | null
  specSummary: string
  setSpecSummary: React.Dispatch<React.SetStateAction<string>>
  pliegoItemStates: Record<string, PliegoItemState>
  setPliegoItemStates: React.Dispatch<React.SetStateAction<Record<string, PliegoItemState>>>
  onPersist: () => Promise<void>
  specSaveBusy: boolean
  flowMsg: string | null
}

export function WorkspaceEspecificacionesTab({
  projectUuid,
  token,
  specSummary,
  setSpecSummary,
  pliegoItemStates,
  setPliegoItemStates,
  onPersist,
  specSaveBusy,
  flowMsg,
}: WorkspaceEspecificacionesTabProps) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-ink">Pliego de condiciones (GA-FO-01)</h2>
      <PliegoCondicionesForm
        projectUuid={projectUuid}
        token={token}
        specSummary={specSummary}
        onSpecSummaryChange={setSpecSummary}
        itemStates={pliegoItemStates}
        onItemStatesChange={setPliegoItemStates}
        onPersist={onPersist}
        persistBusy={specSaveBusy}
        flowMsg={flowMsg}
      />
    </div>
  )
}
