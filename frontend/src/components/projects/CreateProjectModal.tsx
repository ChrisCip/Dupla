import { PrimaryButton } from '../PrimaryButton'

type CreateProjectModalProps = {
  onClose: () => void
  onSubmit: (e: React.FormEvent) => void
  name: string
  setName: React.Dispatch<React.SetStateAction<string>>
  client: string
  setClient: React.Dispatch<React.SetStateAction<string>>
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
