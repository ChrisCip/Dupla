import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { PrimaryButton } from '../components/PrimaryButton'
import { useAuthStore } from '../store/authStore'
import { useWorkspaceStore } from '../store/workspaceStore'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function ProjectWorkspacePage() {
  const { projectUuid = '' } = useParams()
  const token = useAuthStore((s) => s.token)
  const load = useWorkspaceStore((s) => s.load)
  const reset = useWorkspaceStore((s) => s.reset)
  const data = useWorkspaceStore((s) => s.data)
  const status = useWorkspaceStore((s) => s.status)
  const lastSavedAt = useWorkspaceStore((s) => s.lastSavedAt)
  const lastError = useWorkspaceStore((s) => s.lastError)
  const addGroup = useWorkspaceStore((s) => s.addGroup)
  const addItem = useWorkspaceStore((s) => s.addItem)
  const updateItem = useWorkspaceStore((s) => s.updateItem)

  const [kind, setKind] = useState<'tirada' | 'plano' | 'fase'>('fase')
  const [title, setTitle] = useState('Nueva sección')

  useEffect(() => {
    if (!projectUuid) return
    void load(projectUuid)
    return () => reset()
  }, [load, projectUuid, reset])

  const statusLabel = useMemo(() => {
    if (status === 'saving') return 'Guardando…'
    if (status === 'saved') return 'Guardado'
    if (status === 'error') return 'Error al guardar'
    return 'Listo'
  }, [status])

  async function exportFile(path: string, filename: string) {
    if (!token) return
    const res = await apiFetch(path, { token })
    if (!res.ok) return
    const blob = await res.blob()
    downloadBlob(blob, filename)
  }

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-black/5">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-5">
          <div>
            <div className="text-xs text-muted">
              <Link className="hover:underline" to="/app">
                ← Proyectos
              </Link>
            </div>
            <div className="mt-2 text-xl font-bold tracking-tight text-primary">Workspace</div>
            <div className="text-xs text-muted">
              {statusLabel}
              {lastSavedAt ? ` · último: ${new Date(lastSavedAt).toLocaleString()}` : ''}
            </div>
            {lastError ? <div className="mt-2 text-xs text-primary">{lastError}</div> : null}
          </div>
          <div className="flex flex-wrap gap-2">
            <PrimaryButton
              type="button"
              onClick={() =>
                void exportFile(`/api/projects/${projectUuid}/exports/pliego.xlsx`, `pliego-${projectUuid}.xlsx`)
              }
            >
              Pliego (Excel)
            </PrimaryButton>
            <PrimaryButton
              type="button"
              onClick={() =>
                void exportFile(`/api/projects/${projectUuid}/exports/pliego.pdf`, `pliego-${projectUuid}.pdf`)
              }
            >
              Pliego (PDF)
            </PrimaryButton>
            <PrimaryButton
              type="button"
              onClick={() =>
                void exportFile(
                  `/api/projects/${projectUuid}/exports/control-planos.xlsx`,
                  `control-planos-${projectUuid}.xlsx`,
                )
              }
            >
              Control planos (Excel)
            </PrimaryButton>
            <PrimaryButton
              type="button"
              onClick={() =>
                void exportFile(
                  `/api/projects/${projectUuid}/exports/control-planos.pdf`,
                  `control-planos-${projectUuid}.pdf`,
                )
              }
            >
              Control planos (PDF)
            </PrimaryButton>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <section className="rounded-xl border border-black/10 p-4">
          <div className="text-sm font-semibold text-ink">Agregar sección</div>
          <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-end">
            <label className="block text-sm text-muted">
              Tipo
              <select
                className="mt-1 w-full rounded-md border border-black/15 px-3 py-2 text-sm text-ink md:w-56"
                value={kind}
                onChange={(e) => setKind(e.target.value as typeof kind)}
              >
                <option value="tirada">Tirada</option>
                <option value="plano">Plano</option>
                <option value="fase">Fase</option>
              </select>
            </label>
            <label className="block flex-1 text-sm text-muted">
              Título
              <input
                className="mt-1 w-full rounded-md border border-black/15 px-3 py-2 text-sm"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <PrimaryButton type="button" onClick={() => addGroup(kind, title)}>
              Agregar sección
            </PrimaryButton>
          </div>
        </section>

        <div className="mt-8 space-y-6">
          {data.groups.map((g) => (
            <section key={g.id} className="rounded-xl border border-black/10">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-black/5 px-4 py-3">
                <div>
                  <div className="text-xs uppercase tracking-wide text-muted">{g.kind}</div>
                  <div className="text-lg font-semibold text-ink">{g.title}</div>
                </div>
                <PrimaryButton type="button" onClick={() => addItem(g.id)}>
                  + Ítem
                </PrimaryButton>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[900px] text-left text-sm">
                  <thead className="bg-black/[0.02] text-xs uppercase text-muted">
                    <tr>
                      <th className="px-4 py-2">Partida</th>
                      <th className="px-4 py-2">Descripción</th>
                      <th className="px-4 py-2">Unidad</th>
                      <th className="px-4 py-2">Cantidad</th>
                      <th className="px-4 py-2">P. unitario</th>
                      <th className="px-4 py-2">Subtotal</th>
                      <th className="px-4 py-2">Notas</th>
                    </tr>
                  </thead>
                  <tbody>
                    {g.items.map((it) => (
                      <tr key={it.id} className="border-t border-black/5">
                        <td className="px-4 py-2 align-top">
                          <input
                            className="w-28 rounded border border-black/10 px-2 py-1"
                            defaultValue={it.partida ?? ''}
                            onBlur={(e) => updateItem(g.id, it.id, { partida: e.target.value || null })}
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="w-full min-w-[240px] rounded border border-black/10 px-2 py-1"
                            defaultValue={it.descripcion}
                            onBlur={(e) => updateItem(g.id, it.id, { descripcion: e.target.value })}
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="w-20 rounded border border-black/10 px-2 py-1"
                            defaultValue={it.unidad ?? ''}
                            onBlur={(e) => updateItem(g.id, it.id, { unidad: e.target.value || null })}
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="w-24 rounded border border-black/10 px-2 py-1"
                            type="number"
                            defaultValue={it.cantidad ?? 0}
                            onBlur={(e) =>
                              updateItem(g.id, it.id, { cantidad: Number(e.target.value) || 0 })
                            }
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="w-28 rounded border border-black/10 px-2 py-1"
                            type="number"
                            defaultValue={it.precio_unitario ?? 0}
                            onBlur={(e) =>
                              updateItem(g.id, it.id, { precio_unitario: Number(e.target.value) || 0 })
                            }
                          />
                        </td>
                        <td className="px-4 py-2 align-top text-sm text-ink">{String(it.subtotal ?? 0)}</td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="w-44 rounded border border-black/10 px-2 py-1"
                            defaultValue={it.notas ?? ''}
                            onBlur={(e) => updateItem(g.id, it.id, { notas: e.target.value || null })}
                          />
                        </td>
                      </tr>
                    ))}
                    {g.items.length === 0 ? (
                      <tr>
                        <td className="px-4 py-6 text-sm text-muted" colSpan={7}>
                          No hay ítems en esta sección.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          ))}

          {data.groups.length === 0 ? (
            <div className="rounded-xl border border-dashed border-black/15 p-10 text-center text-sm text-muted">
              Agrega una sección para comenzar.
            </div>
          ) : null}
        </div>
      </main>
    </div>
  )
}
