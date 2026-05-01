import { BusinessPliegoForm } from '../../BusinessPliegoForm'
import { PliegoCondicionesForm } from '../../PliegoCondicionesForm'
import type { BusinessPliegoSectionKey } from '../../../constants/businessPliego'
import type { PliegoItemState } from '../../../types/pliegoForm'

type WorkspaceEspecificacionesTabProps = {
  projectUuid: string
  token: string | null
  role: string | null
  specSummary: string
  setSpecSummary: React.Dispatch<React.SetStateAction<string>>
  pliegoItemStates: Record<string, PliegoItemState>
  setPliegoItemStates: React.Dispatch<React.SetStateAction<Record<string, PliegoItemState>>>
  onPersist: () => Promise<void>
  specSaveBusy: boolean
  flowMsg: string | null
  businessSections: Record<BusinessPliegoSectionKey, string>
  onBusinessSectionChange: (key: BusinessPliegoSectionKey, value: string) => void
  onGeneratePliego: (force: boolean) => Promise<void>
  onApprovePliego: () => Promise<void>
  pliegoGenerateBusy: boolean
  pliegoApproveBusy: boolean
  pliegoApproved: boolean
  pliegoGeneratedAt: string | null
}

export function WorkspaceEspecificacionesTab({
  projectUuid,
  token,
  role,
  specSummary,
  setSpecSummary,
  pliegoItemStates,
  setPliegoItemStates,
  onPersist,
  specSaveBusy,
  flowMsg,
  businessSections,
  onBusinessSectionChange,
  onGeneratePliego,
  onApprovePliego,
  pliegoGenerateBusy,
  pliegoApproveBusy,
  pliegoApproved,
  pliegoGeneratedAt,
}: WorkspaceEspecificacionesTabProps) {
  const canApprove = role === 'GERENCIA' || role === 'ARQUITECTURA'
  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-ink">Pliego de condiciones</h2>
      <BusinessPliegoForm
        sections={businessSections}
        onSectionChange={onBusinessSectionChange}
        onGenerate={onGeneratePliego}
        onApprove={onApprovePliego}
        generateBusy={pliegoGenerateBusy}
        approveBusy={pliegoApproveBusy}
        saveBusy={specSaveBusy}
        onSave={onPersist}
        approved={pliegoApproved}
        generatedAt={pliegoGeneratedAt}
        canApprove={canApprove}
        flowMsg={flowMsg}
      />
      <h2 className="text-lg font-semibold text-ink">Formulario GA-FO-01 (ítems)</h2>
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
