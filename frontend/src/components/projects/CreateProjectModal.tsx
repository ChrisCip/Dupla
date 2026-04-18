import { PrimaryButton } from '../PrimaryButton'
import { PROJECT_KIND_OPTIONS, type ProjectKindValue } from '../../constants/projectKind'

type CreateProjectModalProps = {
  onClose: () => void
  onSubmit: (e: React.FormEvent) => void
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
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-black/10 bg-white p-6 shadow-lg"
        role="dialog"
        aria-labelledby="create-project-title"
        aria-modal="true"
      >
        <h2 id="create-project-title" className="text-lg font-semibold text-ink">
          Nuevo proyecto
        </h2>
        <p className="mt-2 text-sm text-muted">
          El nombre puede ser el código interno o la obra; el cliente ayuda a filtrar después. Los participantes se pueden
          ajustar después en <strong className="text-ink">Configuración</strong> del workspace.
        </p>
        <form onSubmit={onSubmit} className="mt-4 space-y-4">
          <div>
            <div className="du-label">Tipo de proyecto</div>
            <div className="mt-2 space-y-2">
              {PROJECT_KIND_OPTIONS.map((o) => (
                <label
                  key={o.value}
                  className={`flex cursor-pointer gap-3 rounded-lg border p-3 text-sm ${
                    projectKind === o.value ? 'border-primary/40 bg-primary/[0.06]' : 'border-black/10 bg-white'
                  }`}
                >
                  <input
                    type="radio"
                    name="project-kind"
                    className="mt-1"
                    checked={projectKind === o.value}
                    onChange={() => setProjectKind(o.value)}
                    disabled={submitting}
                  />
                  <span>
                    <span className="font-medium text-ink">{o.label}</span>
                    <span className="mt-0.5 block text-xs text-muted">{o.description}</span>
                  </span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <label htmlFor="modal-project-name" className="du-label">
              Nombre
            </label>
            <input
              id="modal-project-name"
              className="du-input mt-1"
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-label="Nombre del proyecto"
              disabled={submitting}
              required
              autoFocus
            />
          </div>
          <div>
            <label htmlFor="modal-project-client" className="du-label">
              Cliente <span className="font-normal text-muted">(opcional)</span>
            </label>
            <input
              id="modal-project-client"
              className="du-input mt-1"
              placeholder="Ej. Constructora …"
              value={client}
              onChange={(e) => setClient(e.target.value)}
              aria-label="Cliente"
              disabled={submitting}
            />
          </div>
          {projectKind === 'TENDER' ? (
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
          <div>
            <div className="du-label">Participantes (opcional)</div>
            <p className="mt-1 text-xs text-muted">
              El creador ({userUuid ? 'tú' : 'admin'}) tiene acceso siempre. Marca quién más entra al equipo.
            </p>
            <ul className="mt-2 max-h-40 space-y-2 overflow-y-auto rounded-md border border-black/10 p-2 text-sm">
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
          {error ? <p className="text-sm font-medium text-primary">{error}</p> : null}
          <div className="flex flex-wrap gap-2 pt-2">
            <PrimaryButton className="min-w-[7rem]" type="submit" disabled={submitting}>
              {submitting ? 'Creando…' : 'Crear proyecto'}
            </PrimaryButton>
            <button
              type="button"
              className="rounded-md border border-black/15 bg-white px-4 py-2 text-sm font-medium text-ink hover:bg-black/[0.04]"
              disabled={submitting}
              onClick={onClose}
            >
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
