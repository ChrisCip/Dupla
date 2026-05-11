import { useAuthStore } from '../../../store/authStore'
import { PliegoCondicionesForm } from '../../PliegoCondicionesForm'
import { PliegoSideRail } from '../PliegoSideRail'
import type { PliegoItemState } from '../../../types/pliegoForm'

type WorkspaceEspecificacionesTabProps = {
  projectUuid: string
  projectDisplayName: string
  token: string | null
  role: string | null
  pliegoItemStates: Record<string, PliegoItemState>
  setPliegoItemStates: React.Dispatch<React.SetStateAction<Record<string, PliegoItemState>>>
  onPersist: () => Promise<void>
  specSaveBusy: boolean
  flowMsg: string | null
  onApprovePliego: () => Promise<void>
  pliegoApproveBusy: boolean
  pliegoApproved: boolean
  pliegoGeneratedAt: string | null
  onExportPliegoPdf?: () => void
  onExportPliegoXlsx?: () => void
}

export function WorkspaceEspecificacionesTab({
  projectUuid,
  projectDisplayName,
  token,
  role,
  pliegoItemStates,
  setPliegoItemStates,
  onPersist,
  specSaveBusy,
  flowMsg,
  onApprovePliego,
  pliegoApproveBusy,
  pliegoApproved,
  pliegoGeneratedAt,
  onExportPliegoPdf,
  onExportPliegoXlsx,
}: WorkspaceEspecificacionesTabProps) {
  const userUuid = useAuthStore((s) => s.userUuid)
  const canApprove = role === 'GERENCIA' || role === 'ARQUITECTURA'

  return (
    <div className="flex min-h-0 flex-col gap-6 lg:flex-row lg:items-start lg:gap-6">
      <div className="min-w-0 flex-1">
        <PliegoCondicionesForm
          projectUuid={projectUuid}
          token={token}
          documentTitle={`Pliego de condiciones — ${projectDisplayName}`}
          itemStates={pliegoItemStates}
          onItemStatesChange={setPliegoItemStates}
          onPersist={onPersist}
          persistBusy={specSaveBusy}
          flowMsg={flowMsg}
          onExportPdf={onExportPliegoPdf}
          onExportXlsx={onExportPliegoXlsx}
        />
      </div>

      <PliegoSideRail
        projectUuid={projectUuid}
        token={token}
        userUuid={userUuid}
        itemStates={pliegoItemStates}
        approved={pliegoApproved}
        generatedAt={pliegoGeneratedAt}
        canApprove={canApprove}
        approveBusy={pliegoApproveBusy}
        onApprove={onApprovePliego}
      />
    </div>
  )
}
