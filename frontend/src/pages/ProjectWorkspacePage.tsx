import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { Card } from '../components/Card'
import { PrimaryButton } from '../components/PrimaryButton'
import { StatusBadge } from '../components/StatusBadge'
import { Tabs } from '../components/Tabs'
import { useAuthStore } from '../store/authStore'
import { useWorkspaceStore } from '../store/workspaceStore'

type ProjectMeta = {
  uuid: string
  name: string
  client_name: string | null
  status: string
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function filenameFromContentDisposition(res: Response, fallback: string) {
  const cd = res.headers.get('content-disposition')
  if (!cd) return fallback
  const star = /filename\*=UTF-8''([^;\s]+)/i.exec(cd)
  if (star?.[1]) {
    try {
      return decodeURIComponent(star[1].trim())
    } catch {
      return fallback
    }
  }
  const quoted = /filename="([^"]+)"/i.exec(cd)
  if (quoted?.[1]) return quoted[1]
  const plain = /filename=([^;\s]+)/i.exec(cd)
  if (plain?.[1]) return plain[1].replace(/^"|"$/g, '')
  return fallback
}

const WORKSPACE_TABS = [
  { id: 'detalles', label: 'Detalles' },
  { id: 'pliegos', label: 'Pliegos' },
  { id: 'materiales', label: 'Materiales' },
] as const

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
  const addMaterial = useWorkspaceStore((s) => s.addMaterial)
  const updateMaterial = useWorkspaceStore((s) => s.updateMaterial)
  const removeMaterial = useWorkspaceStore((s) => s.removeMaterial)

  const [tab, setTab] = useState<string>('detalles')
  const [kind, setKind] = useState<'tirada' | 'plano' | 'fase'>('fase')
  const [title, setTitle] = useState('Nueva sección')
  const [project, setProject] = useState<ProjectMeta | null>(null)
  const [projectError, setProjectError] = useState<string | null>(null)

  useEffect(() => {
    if (!projectUuid) return
    void load(projectUuid)
    return () => reset()
  }, [load, projectUuid, reset])

  useEffect(() => {
    if (!projectUuid || !token) return
    let cancelled = false
    async function run() {
      setProjectError(null)
      const res = await apiFetch(`/api/projects/${projectUuid}`, { token })
      if (!res.ok) {
        if (!cancelled) setProjectError('No se pudieron cargar los datos del proyecto')
        return
      }
      const body = (await res.json()) as ProjectMeta
      if (!cancelled) setProject(body)
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [projectUuid, token])

  async function exportFile(path: string, filename: string) {
    if (!token) return
    const res = await apiFetch(path, { token })
    if (!res.ok) return
    const blob = await res.blob()
    downloadBlob(blob, filenameFromContentDisposition(res, filename))
  }

  const displayTitle = project?.name ?? 'Proyecto'

  return (
    <>
      <div className="mb-8 flex flex-col gap-6 border-b border-black/10 pb-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="du-meta">
            <Link className="font-medium text-primary hover:underline" to="/app/projects">
              ← Proyectos
            </Link>
          </div>
          <h1 id="workspace-heading" className="mt-2 text-xl font-bold tracking-tight text-ink">
            {displayTitle}
          </h1>
          <p className="mt-1 du-meta">Workspace del proyecto</p>
        </div>
        <div className="flex w-full flex-col gap-4 sm:w-auto sm:items-end">
          <StatusBadge status={status} lastSavedAt={lastSavedAt} errorMessage={lastError} />
          <div className="flex w-full flex-wrap gap-2 sm:justify-end">
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
      </div>
      <Tabs tabs={[...WORKSPACE_TABS]} value={tab} onChange={setTab} labelledBy="workspace-heading">
        {tab === 'detalles' ? (
          <Card className="p-6">
            <h2 className="text-lg font-semibold text-ink">Detalles del proyecto</h2>
            {projectError ? <p className="mt-3 text-sm text-primary">{projectError}</p> : null}
            {!project && !projectError ? (
              <p className="mt-3 text-sm text-muted">Cargando…</p>
            ) : null}
            {project ? (
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
                  <dt className="du-meta">Estado</dt>
                  <dd className="mt-1 text-sm text-ink">{project.status}</dd>
                </div>
                <div>
                  <dt className="du-meta">Identificador</dt>
                  <dd className="mt-1 font-mono text-xs text-muted">{project.uuid}</dd>
                </div>
              </dl>
            ) : null}
          </Card>
        ) : null}

        {tab === 'pliegos' ? (
          <div className="space-y-8">
            <Card className="p-4">
              <div className="text-sm font-semibold text-ink">Agregar sección</div>
              <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-end">
                <label className="block text-sm text-muted">
                  Tipo
                  <select
                    className="du-input mt-1 md:w-56"
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
                    className="du-input mt-1"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    aria-label="Título de la sección"
                  />
                </label>
                <PrimaryButton type="button" onClick={() => addGroup(kind, title)}>
                  Agregar sección
                </PrimaryButton>
              </div>
            </Card>

            <div className="space-y-6">
              {data.groups.map((g) => (
                <Card key={g.id} className="overflow-hidden p-0">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-black/5 bg-white px-4 py-3">
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
                      <thead className="sticky top-0 z-10 bg-black/[0.04] text-xs uppercase text-muted">
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
                          <tr key={it.id} className="border-t border-black/5 odd:bg-black/[0.015]">
                            <td className="px-4 py-2 align-top">
                              <input
                                className="du-input w-28 py-1.5 text-sm"
                                value={it.partida ?? ''}
                                onChange={(e) => updateItem(g.id, it.id, { partida: e.target.value || null })}
                                aria-label="Partida"
                              />
                            </td>
                            <td className="px-4 py-2 align-top">
                              <input
                                className="du-input min-w-[240px] py-1.5 text-sm"
                                value={it.descripcion}
                                onChange={(e) => updateItem(g.id, it.id, { descripcion: e.target.value })}
                                aria-label="Descripción"
                              />
                            </td>
                            <td className="px-4 py-2 align-top">
                              <input
                                className="du-input w-20 py-1.5 text-sm"
                                value={it.unidad ?? ''}
                                onChange={(e) => updateItem(g.id, it.id, { unidad: e.target.value || null })}
                                aria-label="Unidad"
                              />
                            </td>
                            <td className="px-4 py-2 align-top">
                              <input
                                className="du-input w-24 py-1.5 text-sm"
                                type="number"
                                min={0}
                                step="any"
                                value={it.cantidad ?? ''}
                                onChange={(e) => {
                                  const v = e.target.value
                                  updateItem(g.id, it.id, {
                                    cantidad: v === '' ? 0 : Number(v),
                                  })
                                }}
                                aria-label="Cantidad"
                              />
                            </td>
                            <td className="px-4 py-2 align-top">
                              <input
                                className="du-input w-28 py-1.5 text-sm"
                                type="number"
                                min={0}
                                step="any"
                                value={it.precio_unitario ?? ''}
                                onChange={(e) => {
                                  const v = e.target.value
                                  updateItem(g.id, it.id, {
                                    precio_unitario: v === '' ? 0 : Number(v),
                                  })
                                }}
                                aria-label="Precio unitario"
                              />
                            </td>
                            <td className="px-4 py-2 align-top text-sm tabular-nums text-ink">
                              {(it.subtotal ?? 0).toLocaleString(undefined, {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })}
                            </td>
                            <td className="px-4 py-2 align-top">
                              <input
                                className="du-input w-44 py-1.5 text-sm"
                                value={it.notas ?? ''}
                                onChange={(e) => updateItem(g.id, it.id, { notas: e.target.value || null })}
                                aria-label="Notas"
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
                </Card>
              ))}

              {data.groups.length === 0 ? (
                <Card className="border-dashed p-10 text-center text-sm text-muted">
                  Agrega una sección para comenzar.
                </Card>
              ) : null}
            </div>
          </div>
        ) : null}

        {tab === 'materiales' ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="max-w-prose text-sm text-muted">
                Cubicación e insumos. El total se calcula a partir de la cantidad estimada y el desperdicio (%).
              </p>
              <PrimaryButton type="button" onClick={() => addMaterial()}>
                + Material
              </PrimaryButton>
            </div>

            <Card className="overflow-hidden p-0">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[960px] text-left text-sm">
                  <thead className="sticky top-0 z-10 bg-black/[0.04] text-xs uppercase text-muted">
                    <tr>
                      <th className="px-4 py-2">Categoría</th>
                      <th className="px-4 py-2">Descripción</th>
                      <th className="px-4 py-2">Unidad</th>
                      <th className="px-4 py-2">Cant. est.</th>
                      <th className="px-4 py-2">Desp. %</th>
                      <th className="px-4 py-2">Cant. total</th>
                      <th className="px-4 py-2">Costo est.</th>
                      <th className="px-4 py-2">Proveedor</th>
                      <th className="px-4 py-2" aria-label="Acciones" />
                    </tr>
                  </thead>
                  <tbody>
                    {data.materiales.map((m) => (
                      <tr key={m.id} className="border-t border-black/5 odd:bg-black/[0.015]">
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input w-28 py-1.5 text-sm"
                            value={m.categoria ?? ''}
                            onChange={(e) => updateMaterial(m.id, { categoria: e.target.value || null })}
                            aria-label="Categoría"
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input min-w-[200px] py-1.5 text-sm"
                            value={m.descripcion}
                            onChange={(e) => updateMaterial(m.id, { descripcion: e.target.value })}
                            aria-label="Descripción"
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input w-20 py-1.5 text-sm"
                            value={m.unidad ?? ''}
                            onChange={(e) => updateMaterial(m.id, { unidad: e.target.value || null })}
                            aria-label="Unidad"
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input w-24 py-1.5 text-sm"
                            type="number"
                            min={0}
                            step="any"
                            value={m.cantidad_estimada ?? ''}
                            onChange={(e) => {
                              const v = e.target.value
                              updateMaterial(m.id, {
                                cantidad_estimada: v === '' ? null : Number(v),
                              })
                            }}
                            aria-label="Cantidad estimada"
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input w-20 py-1.5 text-sm"
                            type="number"
                            min={0}
                            max={100}
                            step="any"
                            value={m.desperdicio_porcentaje ?? ''}
                            onChange={(e) => {
                              const v = e.target.value
                              updateMaterial(m.id, {
                                desperdicio_porcentaje: v === '' ? null : Number(v),
                              })
                            }}
                            aria-label="Desperdicio porcentaje"
                          />
                        </td>
                        <td className="px-4 py-2 align-top text-sm tabular-nums text-ink">
                          {m.cantidad_total != null
                            ? m.cantidad_total.toLocaleString(undefined, {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 3,
                              })
                            : '—'}
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input w-28 py-1.5 text-sm"
                            type="number"
                            min={0}
                            step="any"
                            value={m.costo_estimado ?? ''}
                            onChange={(e) => {
                              const v = e.target.value
                              updateMaterial(m.id, {
                                costo_estimado: v === '' ? null : Number(v),
                              })
                            }}
                            aria-label="Costo estimado"
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <input
                            className="du-input w-40 py-1.5 text-sm"
                            value={m.proveedor_sugerido ?? ''}
                            onChange={(e) =>
                              updateMaterial(m.id, { proveedor_sugerido: e.target.value || null })
                            }
                            aria-label="Proveedor sugerido"
                          />
                        </td>
                        <td className="px-4 py-2 align-top">
                          <button
                            type="button"
                            className="text-xs font-semibold text-primary underline-offset-2 hover:underline"
                            onClick={() => removeMaterial(m.id)}
                          >
                            Quitar
                          </button>
                        </td>
                      </tr>
                    ))}
                    {data.materiales.length === 0 ? (
                      <tr>
                        <td className="px-4 py-8 text-center text-sm text-muted" colSpan={9}>
                          No hay materiales. Usa «+ Material» para agregar una fila.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        ) : null}
      </Tabs>
    </>
  )
}
