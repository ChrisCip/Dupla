import { useCallback, useEffect, useState } from 'react'

import { apiFetch } from '../api/client'
import { Card } from './Card'
import { PrimaryButton } from './PrimaryButton'
import type { Project } from '../types/project'

type MemberRow = { uuid: string; email: string }

type ProjectConfigModalProps = {
  open: boolean
  onClose: () => void
  projectUuid: string
  token: string | null
  role: string | null
  project: Project | null
  projectError: string | null
  onProjectSaved: (p: Project) => void
  adminUsers: MemberRow[]
  memberRows: MemberRow[]
  memberSelection: Set<string>
  setMemberSelection: React.Dispatch<React.SetStateAction<Set<string>>>
  membersBusy: boolean
  setMembersBusy: (v: boolean) => void
  membersMsg: string | null
  setMembersMsg: (v: string | null) => void
  setMemberRows: (rows: MemberRow[]) => void
}

export function ProjectConfigModal({
  open,
  onClose,
  projectUuid,
  token,
  role,
  project,
  projectError,
  onProjectSaved,
  adminUsers,
  memberRows,
  memberSelection,
  setMemberSelection,
  membersBusy,
  setMembersBusy,
  membersMsg,
  setMembersMsg,
  setMemberRows,
}: ProjectConfigModalProps) {
  const [name, setName] = useState('')
  const [clientName, setClientName] = useState('')
  const [saveBusy, setSaveBusy] = useState(false)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!open || !project) return
    setName(project.name)
    setClientName(project.client_name ?? '')
    setSaveMsg(null)
  }, [open, project])

  const saveMeta = useCallback(async () => {
    if (!token || !projectUuid || !project) return
    setSaveBusy(true)
    setSaveMsg(null)
    const res = await apiFetch(`/api/projects/${projectUuid}`, {
      method: 'PATCH',
      token,
      body: JSON.stringify({
        name: name.trim() || project.name,
        client_name: clientName.trim() || null,
      }),
    })
    setSaveBusy(false)
    if (!res.ok) {
      setSaveMsg('No se pudo guardar')
      return
    }
    const body = (await res.json()) as Project
    onProjectSaved(body)
    setSaveMsg('Guardado')
  }, [token, projectUuid, project, name, clientName, onProjectSaved])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/45 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="project-config-title"
    >
      <button type="button" className="absolute inset-0 cursor-default" aria-label="Cerrar" onClick={onClose} />
      <div className="relative z-10 flex max-h-[min(92dvh,900px)] w-full max-w-lg flex-col overflow-hidden rounded-xl border border-black/10 bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-black/10 px-4 py-3">
          <h2 id="project-config-title" className="text-lg font-semibold text-ink">
            Configuración del proyecto
          </h2>
          <button
            type="button"
            className="rounded-md px-2 py-1 text-sm text-muted hover:bg-black/[0.04] hover:text-ink"
            onClick={onClose}
          >
            Cerrar
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {projectError ? <p className="mb-3 text-sm text-primary">{projectError}</p> : null}
          {!project ? (
            <p className="text-sm text-muted">Cargando…</p>
          ) : (
            <div className="space-y-6">
              <Card className="p-4">
                <h3 className="text-sm font-semibold text-ink">Datos generales</h3>
                <label className="mt-3 block text-sm text-muted">
                  Nombre
                  <input
                    className="du-input mt-1"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    maxLength={255}
                  />
                </label>
                <label className="mt-3 block text-sm text-muted">
                  Cliente
                  <input
                    className="du-input mt-1"
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    maxLength={255}
                  />
                </label>
                {saveMsg ? <p className="mt-2 text-sm text-primary">{saveMsg}</p> : null}
                <PrimaryButton type="button" className="mt-4" disabled={saveBusy} onClick={() => void saveMeta()}>
                  {saveBusy ? 'Guardando…' : 'Guardar datos'}
                </PrimaryButton>
              </Card>

              <Card className="p-4">
                <h3 className="text-sm font-semibold text-ink">Sistema (solo lectura)</h3>
                <dl className="mt-3 space-y-2 text-sm">
                  <div>
                    <dt className="du-meta">Fase de flujo</dt>
                    <dd className="font-mono text-xs text-ink">{project.workflow_phase}</dd>
                  </div>
                  <div>
                    <dt className="du-meta">Estado técnico legado</dt>
                    <dd className="font-mono text-xs text-ink">{project.status}</dd>
                  </div>
                  <div>
                    <dt className="du-meta">UUID</dt>
                    <dd className="break-all font-mono text-[10px] text-muted/90">{project.uuid}</dd>
                  </div>
                  <div>
                    <dt className="du-meta">Última actualización</dt>
                    <dd className="text-xs text-ink">{new Date(project.updated_at).toLocaleString()}</dd>
                  </div>
                </dl>
              </Card>

              {role === 'GERENCIA' ? (
                <Card className="p-4">
                  <h3 className="text-sm font-semibold text-ink">Equipo con acceso</h3>
                  <p className="mt-1 text-xs text-muted">
                    Además del creador. Todos deben tener módulo Arquitectura.
                  </p>
                  {membersMsg ? <p className="mt-2 text-sm text-primary">{membersMsg}</p> : null}
                  <ul className="mt-3 max-h-48 space-y-2 overflow-y-auto rounded-md border border-black/10 p-3 text-sm">
                    {adminUsers.map((u) => {
                      const isCreator = u.uuid === project.created_by_user_uuid
                      const checked = isCreator || memberSelection.has(u.uuid)
                      return (
                        <li key={u.uuid} className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            id={`cfg-pm-${u.uuid}`}
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
                          <label htmlFor={`cfg-pm-${u.uuid}`} className={isCreator ? 'text-muted' : 'text-ink'}>
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
                            setMemberRows((await m.json()) as MemberRow[])
                          }
                        } finally {
                          setMembersBusy(false)
                        }
                      })()
                    }}
                  >
                    {membersBusy ? 'Guardando…' : 'Guardar acceso'}
                  </PrimaryButton>
                </Card>
              ) : (
                <Card className="p-4">
                  <h3 className="text-sm font-semibold text-ink">Equipo con acceso</h3>
                  <ul className="mt-3 space-y-2 text-sm">
                    {memberRows.length === 0 ? (
                      <li className="text-muted">No hay miembros adicionales.</li>
                    ) : (
                      memberRows.map((r) => <li key={r.uuid}>{r.email}</li>)
                    )}
                  </ul>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
