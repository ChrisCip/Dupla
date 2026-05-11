import { useAuthStore } from '../../../store/authStore'
import { BusinessPliegoForm } from '../../BusinessPliegoForm'
import { PliegoSideRail } from '../PliegoSideRail'
import type { BusinessPliegoSectionKey } from '../../../constants/businessPliego'

type WorkspaceEspecificacionesTabProps = {
  projectUuid: string
  projectDisplayName: string
  token: string | null
  role: string | null
  specSummary: string
  setSpecSummary: React.Dispatch<React.SetStateAction<string>>
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
  onExportPliegoPdf?: () => void
  onExportPliegoXlsx?: () => void
}

export function WorkspaceEspecificacionesTab({
  projectUuid,
  projectDisplayName,
  token,
  role,
  specSummary,
  setSpecSummary,
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
  onExportPliegoPdf,
  onExportPliegoXlsx,
}: WorkspaceEspecificacionesTabProps) {
  const userUuid = useAuthStore((s) => s.userUuid)
  const canApprove = role === 'GERENCIA' || role === 'ARQUITECTURA'

  return (
    <div className="flex min-h-0 flex-col gap-6 lg:flex-row lg:items-start lg:gap-6">
      <div className="min-w-0 flex-1 space-y-8">
        <BusinessPliegoForm
          documentTitle={`Pliego de condiciones — ${projectDisplayName}`}
          sections={businessSections}
          onSectionChange={onBusinessSectionChange}
          specSummary={specSummary}
          onSpecSummaryChange={setSpecSummary}
          onGenerate={onGeneratePliego}
          generateBusy={pliegoGenerateBusy}
          saveBusy={specSaveBusy}
          onSave={onPersist}
          approved={pliegoApproved}
          generatedAt={pliegoGeneratedAt}
          flowMsg={flowMsg}
          onExportPdf={onExportPliegoPdf}
          onExportXlsx={onExportPliegoXlsx}
        />
      </div>

      <PliegoSideRail
        projectUuid={projectUuid}
        token={token}
        userUuid={userUuid}
        sections={businessSections}
        approved={pliegoApproved}
        generatedAt={pliegoGeneratedAt}
        canApprove={canApprove}
        approveBusy={pliegoApproveBusy}
        onApprove={onApprovePliego}
      />
    </div>
  )
}
