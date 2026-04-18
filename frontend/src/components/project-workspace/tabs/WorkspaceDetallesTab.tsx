import { Link } from 'react-router-dom'

import { apiFetch } from '../../../api/client'
import { Card } from '../../Card'
import { PrimaryButton } from '../../PrimaryButton'
import type { Project } from '../../../types/project'

type WorkspaceDetallesTabProps = {
  project: Project | null
  projectError: string | null
  projectUuid: string
  token: string | null
  role: string | null
  phaseLabel: string
  adminUsers: { uuid: string; email: string }[]
  memberSelection: Set<string>
  setMemberSelection: React.Dispatch<React.SetStateAction<Set<string>>>
  membersBusy: boolean
  setMembersBusy: React.Dispatch<React.SetStateAction<boolean>>
  membersMsg: string | null
  setMembersMsg: React.Dispatch<React.SetStateAction<string | null>>
  setMemberRows: React.Dispatch<React.SetStateAction<{ uuid: string; email: string }[]>>
  onOpenChat: () => void
}

export function WorkspaceDetallesTab({
  project,
  projectError,
  projectUuid,
  token,
  role,
  phaseLabel,
  adminUsers,
  memberSelection,
  setMemberSelection,
  membersBusy,
  setMembersBusy,
  membersMsg,
  setMembersMsg,
  setMemberRows,
  onOpenChat,
}: WorkspaceDetallesTabProps) {
  return (
    <Card className="p-6">
      <h2 className="text-lg font-semibold text-ink">Detalles del proyecto</h2>
      {projectError ? <p className="mt-3 text-sm text-primary">{projectError}</p> : null}
      {!project && !projectError ? <p className="mt-3 text-sm text-muted">Cargando…</p> : null}
      {project ? (
        <>
          <dl className="mt-6 grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="du-meta">Nombre</dt>
              <dd className="mt-1 text-sm font-medium text-ink">{project.name}</dd>
            </div>
            <div>
              <dt className="du-meta">Cliente</dt>
              <dd className="mt-1 text-sm text-ink">{project.client_name ?? '—'}</dd>
            </div>
            <div>
              <dt className="du-meta">Estado legado</dt>
              <dd className="mt-1 text-sm text-ink">{project.status}</dd>
            </div>
            <div>
              <dt className="du-meta">Fase del flujo</dt>
              <dd className="mt-1 text-sm font-medium text-ink">{phaseLabel}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="du-meta">Identificador</dt>
              <dd className="mt-1 font-mono text-xs text-muted">{project.uuid}</dd>
            </div>
          </dl>
          <div className="mt-6 flex flex-wrap gap-2">
            <Link className="du-pill-action" to={`/app/tasks?project_uuid=${encodeURIComponent(project.uuid)}`}>
              Tablero del proyecto
            </Link>
            <button type="button" className="du-pill-action" onClick={onOpenChat}>
              Chat del proyecto
            </button>
          </div>
          {role === 'GERENCIA' ? (
            <div className="mt-8 border-t border-black/10 pt-6">
              <h3 className="text-md font-semibold text-ink">Quién puede ver este proyecto</h3>
              <p className="mt-1 text-sm text-muted">
                El creador del proyecto siempre tiene acceso. Marca usuarios con módulo Arquitectura que deben ver el
                workspace.
              </p>
              {membersMsg ? <p className="mt-2 text-sm text-primary">{membersMsg}</p> : null}
              <ul className="mt-4 max-h-56 space-y-2 overflow-y-auto rounded-md border border-black/10 p-3 text-sm">
                {adminUsers.map((u) => {
                  const isCreator = u.uuid === project.created_by_user_uuid
                  const checked = isCreator || memberSelection.has(u.uuid)
                  return (
                    <li key={u.uuid} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id={`pm-${u.uuid}`}
                        className="mt-0.5"
                        checked={checked}
                        disabled={isCreator || membersBusy}
                        onChange={() => {
                          if (isCreator) return
                          setMemberSelection((prev) => {
                            const next = new Set(prev)
                            if (next.has(u.uuid)) next.delete(u.uuid)
                            else next.add(u.uuid)
                            return next
                          })
                        }}
                      />
                      <label htmlFor={`pm-${u.uuid}`} className={isCreator ? 'text-muted' : 'text-ink'}>
                        {u.email}
                        {isCreator ? <span className="du-meta"> (creador)</span> : null}
                      </label>
                    </li>
                  )
                })}
              </ul>
              <PrimaryButton
                type="button"
                className="mt-4"
                disabled={membersBusy}
                onClick={() => {
                  if (!token || !projectUuid) return
                  setMembersBusy(true)
                  setMembersMsg(null)
                  void (async () => {
                    try {
                      const res = await apiFetch(`/api/projects/${projectUuid}/members`, {
                        method: 'PUT',
                        token,
                        body: JSON.stringify({
                          member_user_uuids: Array.from(memberSelection),
                        }),
                      })
                      if (!res.ok) {
                        setMembersMsg('No se pudo guardar la lista de miembros')
                        return
                      }
                      setMembersMsg('Lista de acceso actualizada')
                      const m = await apiFetch(`/api/projects/${projectUuid}/members`, { token })
                      if (m.ok) {
                        setMemberRows((await m.json()) as { uuid: string; email: string }[])
                      }
                    } finally {
                      setMembersBusy(false)
                    }
                  })()
                }}
              >
                {membersBusy ? 'Guardando…' : 'Guardar acceso'}
              </PrimaryButton>
            </div>
          ) : null}
        </>
      ) : null}
    </Card>
  )
}
