import { useCallback, useEffect, useState } from 'react'
import { FilePlus, Filter, FolderPlus, Trash2 } from 'lucide-react'

import { apiFetch } from '../../../api/client'
import {
  PROJECT_FILE_DISCIPLINE_LABELS,
  PROJECT_FILE_DISCIPLINE_VALUES,
  type ProjectFileDisciplineValue,
} from '../../../constants/projectFileDisciplines'
import { downloadBlob } from '../../../lib/download'
import type { ProjectFileFolderRow, ProjectFileRow, ProjectFileSearchRow } from '../../../types/projectWorkspace'
import { Card } from '../../Card'
import { PrimaryButton } from '../../PrimaryButton'
import { ProjectFilesUploadWizard } from '../ProjectFilesUploadWizard'
import { ProjectWorkspaceFileIcon } from '../ProjectWorkspaceFileIcon'

type TrailSeg = { uuid: string | null; name: string }

const FILES_PAGE_SIZE = 50

type FilesListPayload = {
  items: ProjectFileRow[]
  total: number
  limit: number
  offset: number
}

type WorkspaceArchivosTabProps = {
  projectUuid: string
  token: string | null
  flowMsg: string | null
}

function disciplineLabel(raw: string | null | undefined): string | null {
  if (!raw) return null
  const v = raw as ProjectFileDisciplineValue
  return PROJECT_FILE_DISCIPLINE_LABELS[v] ?? raw
}

function formatUploadedAt(iso: string) {
  try {
    return new Date(iso).toLocaleString('es-ES', {
      dateStyle: 'short',
      timeStyle: 'short',
    })
  } catch {
    return iso
  }
}

export function WorkspaceArchivosTab({ projectUuid, token, flowMsg }: WorkspaceArchivosTabProps) {
  const [folderUuid, setFolderUuid] = useState<string | null>(null)
  const [trail, setTrail] = useState<TrailSeg[]>([{ uuid: null, name: 'Raíz' }])
  const [folders, setFolders] = useState<ProjectFileFolderRow[]>([])
  const [files, setFiles] = useState<ProjectFileRow[]>([])
  const [filesTotal, setFilesTotal] = useState(0)
  const [filePageOffset, setFilePageOffset] = useState(0)
  const [busy, setBusy] = useState(false)
  const [wizardOpen, setWizardOpen] = useState(false)
  const [dropHighlight, setDropHighlight] = useState(false)
  const [pendingDropFiles, setPendingDropFiles] = useState<File[] | undefined>(undefined)
  const [folderModalOpen, setFolderModalOpen] = useState(false)
  const [folderModalName, setFolderModalName] = useState('')
  const [filterOpen, setFilterOpen] = useState(false)
  const [filterDiscipline, setFilterDiscipline] = useState<string>('')
  const [filterSearch, setFilterSearch] = useState('')
  const [searchHits, setSearchHits] = useState<ProjectFileSearchRow[] | null>(null)
  const [searchBusy, setSearchBusy] = useState(false)
  const [dragFileId, setDragFileId] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!token || !projectUuid) return
    setBusy(true)
    try {
      const fq =
        folderUuid === null
          ? ''
          : `?parent_uuid=${encodeURIComponent(folderUuid)}`
      const fileParams = new URLSearchParams()
      if (folderUuid !== null) fileParams.set('folder_uuid', folderUuid)
      fileParams.set('limit', String(FILES_PAGE_SIZE))
      fileParams.set('offset', String(filePageOffset))
      const filesUrl = `/api/projects/${projectUuid}/files?${fileParams.toString()}`
      const [fr, fe] = await Promise.all([
        apiFetch(`/api/projects/${projectUuid}/file-folders${fq}`, { token }),
        apiFetch(filesUrl, { token }),
      ])
      if (fr.ok) setFolders((await fr.json()) as ProjectFileFolderRow[])
      if (fe.ok) {
        const data = (await fe.json()) as FilesListPayload
        setFiles(data.items)
        setFilesTotal(data.total)
        if (data.items.length === 0 && data.total > 0 && data.offset >= data.total) {
          setFilePageOffset(0)
        }
      }
    } finally {
      setBusy(false)
    }
  }, [token, projectUuid, folderUuid, filePageOffset])

  useEffect(() => {
    void load()
  }, [load])

  function enterFolder(f: ProjectFileFolderRow) {
    setFilePageOffset(0)
    setFolderUuid(f.uuid)
    setTrail((t) => [...t, { uuid: f.uuid, name: f.name }])
  }

  function goTrail(i: number) {
    setFilePageOffset(0)
    const next = trail.slice(0, i + 1)
    setTrail(next)
    const last = next[next.length - 1]
    setFolderUuid(last?.uuid ?? null)
  }

  const loadSearchResults = useCallback(async () => {
    if (!token || !projectUuid) return
    const params = new URLSearchParams()
    if (filterSearch.trim()) params.set('q', filterSearch.trim())
    if (filterDiscipline) params.set('discipline', filterDiscipline)
    const res = await apiFetch(`/api/projects/${projectUuid}/files/search?${params.toString()}`, { token })
    if (res.ok) setSearchHits((await res.json()) as ProjectFileSearchRow[])
    else setSearchHits([])
  }, [token, projectUuid, filterSearch, filterDiscipline])

  const hasActiveFilters = Boolean(filterDiscipline || filterSearch.trim())

  useEffect(() => {
    if (hasActiveFilters) setFilePageOffset(0)
  }, [hasActiveFilters])

  useEffect(() => {
    if (!hasActiveFilters) {
      setSearchHits(null)
      setSearchBusy(false)
      return
    }
    let cancelled = false
    setSearchBusy(true)
    const t = window.setTimeout(() => {
      void (async () => {
        try {
          await loadSearchResults()
        } finally {
          if (!cancelled) setSearchBusy(false)
        }
      })()
    }, 300)
    return () => {
      cancelled = true
      window.clearTimeout(t)
    }
  }, [hasActiveFilters, loadSearchResults])

  async function createFolderFromModal() {
    if (!token || !folderModalName.trim()) return
    const res = await apiFetch(`/api/projects/${projectUuid}/file-folders`, {
      method: 'POST',
      token,
      body: JSON.stringify({ name: folderModalName.trim(), parent_uuid: folderUuid }),
    })
    if (!res.ok) return
    setFolderModalName('')
    setFolderModalOpen(false)
    await load()
  }

  async function deleteFolder(f: ProjectFileFolderRow) {
    if (!token || !window.confirm(`¿Eliminar carpeta "${f.name}"? (debe estar vacía)`)) return
    const res = await apiFetch(`/api/projects/${projectUuid}/file-folders/${f.uuid}`, {
      method: 'DELETE',
      token,
    })
    if (!res.ok) return
    await load()
  }

  async function deleteFile(f: ProjectFileRow) {
    if (!token || !window.confirm(`¿Eliminar "${f.original_name}"?`)) return
    const res = await apiFetch(`/api/projects/${projectUuid}/files/${f.uuid}`, {
      method: 'DELETE',
      token,
    })
    if (!res.ok) return
    if (hasActiveFilters) await loadSearchResults()
    await load()
  }

  async function downloadFile(f: ProjectFileRow) {
    if (!token) return
    const res = await apiFetch(`/api/projects/${projectUuid}/files/${f.uuid}/download`, { token })
    if (!res.ok) return
    const blob = await res.blob()
    downloadBlob(blob, f.original_name)
  }

  async function moveFileToFolder(fileUuid: string, targetFolderUuid: string | null) {
    if (!token) return
    const res = await apiFetch(`/api/projects/${projectUuid}/files/${fileUuid}`, {
      method: 'PATCH',
      token,
      body: JSON.stringify({ folder_uuid: targetFolderUuid }),
    })
    if (!res.ok) return
    setDragFileId(null)
    await load()
  }

  const currentFolderLabel = trail[trail.length - 1]?.name ?? 'Raíz'

  const fileHasPrevPage = filePageOffset > 0
  const fileHasNextPage = filePageOffset + files.length < filesTotal
  const showFilePagination =
    !hasActiveFilters && filesTotal > 20 && (fileHasPrevPage || fileHasNextPage)

  return (
    <Card className="space-y-4 p-6">
      <div>
        <h2 className="text-lg font-semibold text-ink">Archivos / planos</h2>
        <p className="text-sm text-muted">
          Explorador por carpetas con descripción y disciplina. Arrastra archivos al área inferior o usa Crear
          archivo.
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className={`inline-flex shrink-0 items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium shadow-sm ${
              hasActiveFilters
                ? 'border-primary/40 bg-primary/[0.06] text-primary'
                : 'border-black/15 bg-white text-ink hover:bg-black/[0.03]'
            }`}
            aria-expanded={filterOpen}
            onClick={() => setFilterOpen((o) => !o)}
          >
            <Filter className="h-4 w-4" aria-hidden />
            Filtrar
          </button>
          {showFilePagination ? (
            <>
              {fileHasPrevPage ? (
                <button
                  type="button"
                  className="rounded-lg border border-black/15 bg-white px-3 py-2 text-sm font-medium text-ink shadow-sm hover:bg-black/[0.03]"
                  onClick={() => setFilePageOffset((o) => Math.max(0, o - FILES_PAGE_SIZE))}
                >
                  Ver archivos anteriores
                </button>
              ) : null}
              {fileHasNextPage ? (
                <button
                  type="button"
                  className="rounded-lg border border-black/15 bg-white px-3 py-2 text-sm font-medium text-ink shadow-sm hover:bg-black/[0.03]"
                  onClick={() => setFilePageOffset((o) => o + FILES_PAGE_SIZE)}
                >
                  Ver próximos archivos
                </button>
              ) : null}
            </>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <PrimaryButton type="button" className="shrink-0 gap-2" onClick={() => setWizardOpen(true)}>
            <FilePlus className="h-4 w-4" aria-hidden />
            Crear archivo
          </PrimaryButton>
          <button
            type="button"
            className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-black/15 bg-white px-3 py-2 text-sm font-medium text-ink shadow-sm hover:bg-black/[0.03]"
            onClick={() => {
              setFolderModalName('')
              setFolderModalOpen(true)
            }}
          >
            <FolderPlus className="h-4 w-4 text-muted" aria-hidden />
            Crear carpeta
          </button>
        </div>
      </div>

      {filterOpen ? (
        <div className="flex flex-wrap items-end gap-3 rounded-lg border border-black/10 bg-black/[0.02] p-3">
          <div className="min-w-[10rem] flex-1">
            <label htmlFor="archivos-filter-discipline" className="du-label text-xs">
              Disciplina
            </label>
            <select
              id="archivos-filter-discipline"
              className="du-input mt-1 w-full text-sm"
              value={filterDiscipline}
              onChange={(e) => setFilterDiscipline(e.target.value)}
            >
              <option value="">Todas</option>
              {PROJECT_FILE_DISCIPLINE_VALUES.map((v) => (
                <option key={v} value={v}>
                  {PROJECT_FILE_DISCIPLINE_LABELS[v]}
                </option>
              ))}
            </select>
          </div>
          <div className="min-w-[12rem] flex-[2]">
            <label htmlFor="archivos-filter-search" className="du-label text-xs">
              Nombre o descripción
            </label>
            <input
              id="archivos-filter-search"
              className="du-input mt-1 w-full text-sm"
              value={filterSearch}
              onChange={(e) => setFilterSearch(e.target.value)}
              placeholder="Buscar…"
              autoComplete="off"
            />
          </div>
          {hasActiveFilters ? (
            <button
              type="button"
              className="rounded-lg border border-black/15 px-3 py-2 text-sm text-muted hover:bg-white"
              onClick={() => {
                setFilterDiscipline('')
                setFilterSearch('')
              }}
            >
              Limpiar
            </button>
          ) : null}
        </div>
      ) : null}

      {flowMsg ? <p className="text-sm text-primary">{flowMsg}</p> : null}

      {hasActiveFilters ? (
        <p className="text-sm text-muted">
          Búsqueda en todo el proyecto: solo archivos. La ruta muestra la carpeta donde está cada uno.
        </p>
      ) : (
        <nav className="flex flex-wrap items-center gap-1 text-sm" aria-label="Ruta">
          {trail.map((seg, i) => (
            <span key={`${seg.uuid ?? 'root'}-${i}`} className="flex items-center gap-1">
              {i > 0 ? <span className="text-black/25">/</span> : null}
              <button
                type="button"
                className={`rounded px-1 py-0.5 hover:bg-black/5 ${
                  i === trail.length - 1 ? 'font-semibold text-ink' : 'text-primary'
                }`}
                onClick={() => goTrail(i)}
              >
                {seg.name}
              </button>
            </span>
          ))}
        </nav>
      )}

      <div
        className={`rounded-xl border-2 border-dashed p-4 transition-colors ${
          dropHighlight ? 'border-primary/50 bg-primary/[0.04]' : 'border-black/10 bg-white'
        }`}
        onDragEnter={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setDropHighlight(true)
        }}
        onDragLeave={(e) => {
          e.preventDefault()
          if (e.currentTarget === e.target) setDropHighlight(false)
        }}
        onDragOver={(e) => {
          e.preventDefault()
          e.stopPropagation()
        }}
        onDrop={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setDropHighlight(false)
          if (e.dataTransfer.files?.length) {
            setPendingDropFiles(Array.from(e.dataTransfer.files))
            setWizardOpen(true)
            return
          }
          if (hasActiveFilters) return
          const id = e.dataTransfer.getData('text/plain')
          if (id && dragFileId) void moveFileToFolder(id, folderUuid)
        }}
      >
        {hasActiveFilters ? (
          searchBusy ? (
            <p className="py-8 text-center text-sm text-muted">Buscando…</p>
          ) : searchHits && searchHits.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted">
              Ningún archivo coincide con los filtros. Prueba otro texto o disciplina.
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {(searchHits ?? []).map((f) => (
                <div
                  key={f.uuid}
                  className="group relative flex flex-col gap-2 rounded-xl border border-black/10 bg-white p-4 shadow-[var(--shadow-card)] transition hover:border-primary/25"
                >
                  <div className="flex items-start gap-3">
                    <ProjectWorkspaceFileIcon name={f.original_name} className="h-11 w-11 shrink-0 text-primary" />
                    <div className="min-w-0 flex-1">
                      <p className="line-clamp-2 font-medium text-ink">{f.original_name}</p>
                      <p className="mt-1 text-[11px] leading-snug text-primary" title={f.path}>
                        {f.path}
                      </p>
                      <p className="mt-1 text-[11px] text-muted">Subido: {formatUploadedAt(f.created_at)}</p>
                      {f.ingest_status === 'DRAFT' ? (
                        <span className="mt-1 inline-block rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-900">
                          Borrador
                        </span>
                      ) : null}
                      {disciplineLabel(f.discipline) ? (
                        <span className="mt-1 inline-block rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                          {disciplineLabel(f.discipline)}
                        </span>
                      ) : (
                        <span className="mt-1 inline-block text-[11px] text-muted">Sin clasificar</span>
                      )}
                      {f.description ? (
                        <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-muted">{f.description}</p>
                      ) : (
                        <p className="mt-2 text-xs italic text-muted">Sin descripción</p>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2 border-t border-black/5 pt-2">
                    <button
                      type="button"
                      className="text-xs font-semibold text-primary hover:underline"
                      onClick={() => void downloadFile(f)}
                    >
                      Descargar
                    </button>
                    <button
                      type="button"
                      className="text-xs font-semibold text-red-700 hover:underline"
                      onClick={() => void deleteFile(f)}
                    >
                      Eliminar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )
        ) : busy ? (
          <p className="text-sm text-muted">Cargando…</p>
        ) : folders.length === 0 && files.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted">
            Carpeta vacía. Crea una carpeta, un archivo o arrastra aquí.
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {folders.map((fo) => (
              <div
                key={fo.uuid}
                role="button"
                tabIndex={0}
                className="group relative flex flex-col gap-2 rounded-xl border border-black/10 bg-white p-4 text-left shadow-[var(--shadow-card)] transition hover:border-primary/25"
                onDoubleClick={() => enterFolder(fo)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') enterFolder(fo)
                }}
                onDragOver={(e) => {
                  e.preventDefault()
                  if (dragFileId) e.dataTransfer.dropEffect = 'move'
                }}
                onDrop={(e) => {
                  e.preventDefault()
                  const id = e.dataTransfer.getData('text/plain')
                  if (id && dragFileId) void moveFileToFolder(id, fo.uuid)
                }}
              >
                <div className="flex items-start gap-3">
                  <ProjectWorkspaceFileIcon isFolder name={fo.name} className="h-11 w-11 shrink-0 text-amber-600/90" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-ink">{fo.name}</p>
                    <p className="text-xs text-muted">Carpeta</p>
                  </div>
                  <button
                    type="button"
                    className="shrink-0 rounded p-1 text-muted opacity-0 hover:bg-red-50 hover:text-red-700 group-hover:opacity-100"
                    title="Eliminar carpeta"
                    onClick={(e) => {
                      e.stopPropagation()
                      void deleteFolder(fo)
                    }}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </button>
                </div>
              </div>
            ))}

            {files.map((f) => (
              <div
                key={f.uuid}
                draggable
                className="group relative flex flex-col gap-2 rounded-xl border border-black/10 bg-white p-4 shadow-[var(--shadow-card)] transition hover:border-primary/25"
                onDragStart={(e) => {
                  setDragFileId(f.uuid)
                  e.dataTransfer.setData('text/plain', f.uuid)
                  e.dataTransfer.effectAllowed = 'move'
                }}
                onDragEnd={() => setDragFileId(null)}
              >
                <div className="flex items-start gap-3">
                  <ProjectWorkspaceFileIcon name={f.original_name} className="h-11 w-11 shrink-0 text-primary" />
                  <div className="min-w-0 flex-1">
                    <p className="line-clamp-2 font-medium text-ink">{f.original_name}</p>
                    <p className="mt-1 text-[11px] text-muted">Subido: {formatUploadedAt(f.created_at)}</p>
                    {f.ingest_status === 'DRAFT' ? (
                      <span className="mt-1 inline-block rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-900">
                        Borrador
                      </span>
                    ) : null}
                    {disciplineLabel(f.discipline) ? (
                      <span className="mt-1 inline-block rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                        {disciplineLabel(f.discipline)}
                      </span>
                    ) : (
                      <span className="mt-1 inline-block text-[11px] text-muted">Sin clasificar</span>
                    )}
                    {f.description ? (
                      <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-muted">{f.description}</p>
                    ) : (
                      <p className="mt-2 text-xs italic text-muted">Sin descripción</p>
                    )}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 border-t border-black/5 pt-2">
                  <button
                    type="button"
                    className="text-xs font-semibold text-primary hover:underline"
                    onClick={() => void downloadFile(f)}
                  >
                    Descargar
                  </button>
                  <button
                    type="button"
                    className="text-xs font-semibold text-red-700 hover:underline"
                    onClick={() => void deleteFile(f)}
                  >
                    Eliminar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <p className="text-xs text-muted">
        {hasActiveFilters
          ? 'Sal de los filtros (Limpiar) para volver a la vista por carpetas y mover archivos.'
          : 'Arrastra un archivo sobre una carpeta para moverlo. Doble clic en una carpeta para abrirla.'}
      </p>

      <ProjectFilesUploadWizard
        open={wizardOpen}
        onClose={() => {
          setWizardOpen(false)
          setPendingDropFiles(undefined)
        }}
        projectUuid={projectUuid}
        token={token}
        defaultFolderUuid={folderUuid}
        defaultFolderLabel={currentFolderLabel}
        initialFiles={pendingDropFiles}
        onCompleted={() => void load()}
      />

      {folderModalOpen ? (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setFolderModalOpen(false)
          }}
        >
          <div
            className="w-full max-w-md rounded-xl border border-black/10 bg-white p-6 shadow-xl"
            role="dialog"
            aria-labelledby="folder-modal-title"
            aria-modal="true"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <h3 id="folder-modal-title" className="text-lg font-semibold text-ink">
              Nueva carpeta
            </h3>
            <p className="mt-1 text-sm text-muted">
              Se creará dentro de &ldquo;{currentFolderLabel}&rdquo;.
            </p>
            <label htmlFor="folder-modal-name" className="du-label mt-4 block text-xs">
              Nombre
            </label>
            <input
              id="folder-modal-name"
              className="du-input mt-1 w-full text-sm"
              value={folderModalName}
              onChange={(e) => setFolderModalName(e.target.value)}
              placeholder="Nombre de carpeta"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') void createFolderFromModal()
              }}
            />
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg border border-black/15 px-4 py-2 text-sm font-medium hover:bg-black/5"
                onClick={() => setFolderModalOpen(false)}
              >
                Cancelar
              </button>
              <PrimaryButton
                type="button"
                disabled={!folderModalName.trim() || busy}
                onClick={() => void createFolderFromModal()}
              >
                Crear
              </PrimaryButton>
            </div>
          </div>
        </div>
      ) : null}
    </Card>
  )
}
