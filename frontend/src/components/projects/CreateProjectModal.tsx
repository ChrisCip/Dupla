import { useEffect, useMemo, useState } from 'react'

import { DuplaLogo } from '../DuplaLogo'
import { PrimaryButton } from '../PrimaryButton'
import { PROJECT_KIND_OPTIONS, type ProjectKindValue } from '../../constants/projectKind'

const STEP = {
  datos: {
    title: 'Datos generales',
    description:
      'Identifica la obra con un nombre reconocible (código interno, dirección o nombre comercial). El cliente es opcional y ayuda a filtrar y agrupar proyectos después.',
    footerHint: 'Identificación',
  },
  tipo: {
    title: 'Tipo de proyecto',
    description:
      'El tipo define la fase inicial: los residenciales siguen el flujo completo desde criterios de arranque; los de licitación entran en revisión de arquitectura y requieren archivos antes de invitar al equipo.',
    footerHint: 'Tipo',
  },
  archivos: {
    title: 'Archivos de licitación',
    description:
      'Adjunta uno o más archivos (pliegos, PDF, DWG, etc.). Son obligatorios para crear el proyecto de licitación.',
    footerHint: 'Archivos',
  },
  participantes: {
    title: 'Equipo del proyecto',
    description:
      'El creador siempre tiene acceso. Marca quién más debe ver el workspace; puedes cambiarlo después en Configuración.',
    footerHint: 'Participantes',
  },
} as const

function projectKindMaxStep(kind: ProjectKindValue): number {
  return kind === 'TENDER' ? 4 : 3
}

function getStepMeta(step: number, kind: ProjectKindValue): (typeof STEP)[keyof typeof STEP] {
  if (step === 1) return STEP.datos
  if (step === 2) return STEP.tipo
  if (step === 3 && kind === 'TENDER') return STEP.archivos
  if (step === 3 && kind === 'RESIDENTIAL') return STEP.participantes
  if (step === 4) return STEP.participantes
  return STEP.datos
}

function ProjectKindRadio({
  selected,
  onSelect,
  disabled,
  id,
  label,
  description: desc,
}: {
  selected: boolean
  onSelect: () => void
  disabled: boolean
  id: string
  label: string
  description: string
}) {
  return (
    <button
      type="button"
      id={id}
      role="radio"
      aria-checked={selected}
      disabled={disabled}
      onClick={onSelect}
      className={`flex w-full cursor-pointer gap-3 rounded-lg border p-3 text-left text-sm transition-colors ${
        selected ? 'border-primary/40 bg-primary/[0.06]' : 'border-black/10 bg-white hover:border-black/20'
      } ${disabled ? 'cursor-not-allowed opacity-60' : ''}`}
    >
      <span className="mt-0.5 flex shrink-0 items-center justify-center" aria-hidden>
        <span
          className={`flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full border-2 bg-neutral-200/90 ${
            selected ? 'border-primary' : 'border-black/15'
          }`}
        >
          {selected ? <span className="h-2.5 w-2.5 rounded-full bg-primary" /> : null}
        </span>
      </span>
      <span className="min-w-0">
        <span className="font-medium text-ink">{label}</span>
        <span className="mt-0.5 block text-xs text-muted">{desc}</span>
      </span>
    </button>
  )
}

type CreateProjectModalProps = {
  onClose: () => void
  onSubmit: (e?: React.FormEvent) => void
  name: string
  setName: React.Dispatch<React.SetStateAction<string>>
  client: string
  setClient: React.Dispatch<React.SetStateAction<string>>
  projectKind: ProjectKindValue
  setProjectKind: React.Dispatch<React.SetStateAction<ProjectKindValue>>
  createFiles: File[]
  setCreateFiles: React.Dispatch<React.SetStateAction<File[]>>
  createMembers: Set<string>
  setCreateMembers: React.Dispatch<React.SetStateAction<Set<string>>>
  adminUsersCreate: { uuid: string; email: string }[]
  userUuid: string | null
  error: string | null
  submitting: boolean
}

export function CreateProjectModal({
  onClose,
  onSubmit,
  name,
  setName,
  client,
  setClient,
  projectKind,
  setProjectKind,
  createFiles,
  setCreateFiles,
  createMembers,
  setCreateMembers,
  adminUsersCreate,
  userUuid,
  error,
  submitting,
}: CreateProjectModalProps) {
  const [step, setStep] = useState(1)

  const maxStep = projectKindMaxStep(projectKind)
  const stepNumbers = useMemo(() => Array.from({ length: maxStep }, (_, i) => i + 1), [maxStep])

  useEffect(() => {
    setStep((s) => (s > maxStep ? maxStep : s))
  }, [maxStep])

  const canGoNextFromStep1 = name.trim().length > 0
  const stepMeta = getStepMeta(step, projectKind)

  const isLastStep =
    (projectKind === 'RESIDENTIAL' && step === 3) || (projectKind === 'TENDER' && step === 4)

  function goNext() {
    if (step === 1 && !canGoNextFromStep1) return
    if (step >= maxStep) return
    setStep((s) => s + 1)
  }

  function goBack() {
    if (step > 1) setStep((s) => s - 1)
  }

  function handleCreateClick() {
    if (!isLastStep) return
    onSubmit()
  }

  const stepCount = maxStep

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        className="flex h-[80vh] max-h-[80vh] w-full max-w-5xl min-h-0 flex-col overflow-hidden rounded-xl border border-black/10 bg-white shadow-xl md:flex-row"
        role="dialog"
        aria-labelledby="create-project-title"
        aria-modal="true"
      >
        <aside className="flex min-h-0 w-full shrink-0 flex-col border-b border-black/10 bg-gradient-to-br from-primary/[0.08] to-black/[0.02] px-4 py-5 md:w-[15vw] md:min-w-0 md:border-b-0 md:border-r md:py-6">
          <div className="flex justify-center px-2">
            <DuplaLogo className="h-10 w-auto max-w-[min(100%,12rem)] object-contain" />
          </div>
          <div className="mt-4 min-h-0 flex-1 overflow-y-auto">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-primary">Nuevo proyecto</p>
            <h2 id="create-project-title" className="mt-1 text-xl font-semibold leading-snug text-ink">
              {stepMeta.title}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted">{stepMeta.description}</p>
          </div>
          <div className="mt-6 shrink-0 border-t border-black/10 pt-4">
            <div className="flex items-center justify-center gap-1.5" aria-label="Pasos">
              {stepNumbers.map((n) => (
                <span key={n} className="flex items-center gap-1.5">
                  {n > 1 ? <span className="h-px w-5 bg-black/15" aria-hidden /> : null}
                  <span
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                      step === n
                        ? 'bg-primary text-white shadow-sm'
                        : step > n
                          ? 'bg-primary/20 text-primary'
                          : 'border border-black/15 bg-white/80 text-muted'
                    }`}
                  >
                    {n}
                  </span>
                </span>
              ))}
            </div>
            <p className="mt-2 text-center text-[11px] text-muted">
              Paso {step} de {stepCount} — {stepMeta.footerHint}
            </p>
          </div>
        </aside>

        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div
            className="flex min-h-0 flex-1 flex-col overflow-hidden"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !isLastStep) {
                e.preventDefault()
              }
            }}
          >
            <div className="flex min-h-0 flex-1 items-center justify-center overflow-y-auto px-6 py-5 md:px-8 md:py-6">
              <div className="w-full max-w-md">
                {step === 1 ? (
                  <div className="space-y-4">
                    <div>
                      <label htmlFor="modal-project-name" className="du-label">
                        Nombre <span className="text-primary">*</span>
                      </label>
                      <input
                        id="modal-project-name"
                        className="du-input mt-1 w-full"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        aria-label="Nombre del proyecto"
                        disabled={submitting}
                        autoFocus
                      />
                    </div>
                    <div>
                      <label htmlFor="modal-project-client" className="du-label">
                        Cliente <span className="font-normal text-muted">(opcional)</span>
                      </label>
                      <input
                        id="modal-project-client"
                        className="du-input mt-1 w-full"
                        placeholder="Ej. Constructora …"
                        value={client}
                        onChange={(e) => setClient(e.target.value)}
                        aria-label="Cliente"
                        disabled={submitting}
                      />
                    </div>
                  </div>
                ) : null}

                {step === 2 ? (
                  <div>
                    <div className="du-label" id="project-kind-group-label">
                      Selecciona el tipo
                    </div>
                    <div
                      className="mt-3 space-y-2"
                      role="radiogroup"
                      aria-labelledby="project-kind-group-label"
                    >
                      {PROJECT_KIND_OPTIONS.map((o) => (
                        <ProjectKindRadio
                          key={o.value}
                          id={`project-kind-${o.value}`}
                          selected={projectKind === o.value}
                          onSelect={() => setProjectKind(o.value)}
                          disabled={submitting}
                          label={o.label}
                          description={o.description}
                        />
                      ))}
                    </div>
                  </div>
                ) : null}

                {step === 3 && projectKind === 'TENDER' ? (
                  <div>
                    <label htmlFor="modal-project-files" className="du-label">
                      Archivos iniciales <span className="text-primary">(obligatorio)</span>
                    </label>
                    <input
                      id="modal-project-files"
                      type="file"
                      className="mt-1 block w-full text-sm text-ink file:mr-3 file:rounded-md file:border-0 file:bg-primary/12 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-ink"
                      multiple
                      disabled={submitting}
                      onChange={(e) => {
                        const list = e.target.files
                        setCreateFiles(list ? Array.from(list) : [])
                      }}
                    />
                    {createFiles.length > 0 ? (
                      <ul className="mt-2 list-inside list-disc text-xs text-muted">
                        {createFiles.map((f) => (
                          <li key={`${f.name}-${f.size}`}>{f.name}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-1 text-xs text-muted">Selecciona uno o más archivos (DWG, PDF, etc.).</p>
                    )}
                  </div>
                ) : null}

                {((step === 3 && projectKind === 'RESIDENTIAL') || step === 4) ? (
                  <div>
                    <div className="du-label">Participantes (opcional)</div>
                    <p className="mt-1 text-xs text-muted">
                      El creador ({userUuid ? 'tú' : 'admin'}) tiene acceso siempre. Marca quién más entra al equipo.
                    </p>
                    <ul className="mt-2 max-h-36 space-y-2 overflow-y-auto rounded-md border border-black/10 p-2 text-sm">
                      {adminUsersCreate.map((u) => {
                        const isSelf = userUuid !== null && u.uuid === userUuid
                        const checked = isSelf || createMembers.has(u.uuid)
                        return (
                          <li key={u.uuid} className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              id={`cm-${u.uuid}`}
                              className="mt-0.5"
                              checked={checked}
                              disabled={isSelf || submitting}
                              onChange={() => {
                                if (isSelf) return
                                setCreateMembers((prev) => {
                                  const next = new Set(prev)
                                  if (next.has(u.uuid)) next.delete(u.uuid)
                                  else next.add(u.uuid)
                                  return next
                                })
                              }}
                            />
                            <label htmlFor={`cm-${u.uuid}`} className={isSelf ? 'text-muted' : 'text-ink'}>
                              {u.email}
                              {isSelf ? <span className="du-meta"> (creador)</span> : null}
                            </label>
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                ) : null}

                {error ? <p className="mt-4 text-sm font-medium text-primary">{error}</p> : null}
              </div>
            </div>

            <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-black/10 bg-white px-6 py-4 md:px-8">
              <button
                type="button"
                className="rounded-md border border-black/15 bg-white px-4 py-2 text-sm font-medium text-ink hover:bg-black/[0.04]"
                disabled={submitting}
                onClick={onClose}
              >
                Cancelar
              </button>
              <div className="flex flex-wrap gap-2">
                {step > 1 ? (
                  <button
                    type="button"
                    className="rounded-md border border-black/15 bg-white px-4 py-2 text-sm font-medium text-ink hover:bg-black/[0.04]"
                    disabled={submitting}
                    onClick={goBack}
                  >
                    Atrás
                  </button>
                ) : null}
                {isLastStep ? (
                  <PrimaryButton
                    className="min-w-28"
                    type="button"
                    disabled={submitting}
                    onClick={handleCreateClick}
                  >
                    {submitting ? 'Creando…' : 'Crear proyecto'}
                  </PrimaryButton>
                ) : (
                  <PrimaryButton
                    type="button"
                    className="min-w-28"
                    disabled={submitting || (step === 1 && !canGoNextFromStep1)}
                    onClick={goNext}
                  >
                    Siguiente
                  </PrimaryButton>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
