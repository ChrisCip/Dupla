import { apiFetch } from '../../../api/client'
import { Card } from '../../Card'
import { downloadBlob } from '../../../lib/download'
import type { ProjectFileRow } from '../../../types/projectWorkspace'

type WorkspaceArchivosTabProps = {
  projectUuid: string
  token: string | null
  flowMsg: string | null
  fileCategory: string
  setFileCategory: React.Dispatch<React.SetStateAction<string>>
  files: ProjectFileRow[]
  onUploadFileList: (f: FileList | null) => void
}

export function WorkspaceArchivosTab({
  projectUuid,
  token,
  flowMsg,
  fileCategory,
  setFileCategory,
  files,
  onUploadFileList,
}: WorkspaceArchivosTabProps) {
  return (
    <Card className="space-y-4 p-6">
      <h2 className="text-lg font-semibold text-ink">Archivos / planos</h2>
      <p className="text-sm text-muted">Sube DWG/DXF u otros adjuntos. Categoría opcional (nomenclatura).</p>
      {flowMsg ? <p className="text-sm text-primary">{flowMsg}</p> : null}
      <label className="block text-sm text-muted">
        Categoría
        <input className="du-input mt-1" value={fileCategory} onChange={(e) => setFileCategory(e.target.value)} />
      </label>
      <input type="file" className="text-sm" onChange={(e) => void onUploadFileList(e.target.files)} />
      <ul className="divide-y divide-black/10 text-sm">
        {files.map((f) => (
          <li key={f.uuid} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span>{f.original_name}</span>
            <a
              className="font-semibold text-primary underline-offset-2 hover:underline"
              href={`/api/projects/${projectUuid}/files/${f.uuid}/download`}
              onClick={async (e) => {
                e.preventDefault()
                if (!token) return
                const res = await apiFetch(`/api/projects/${projectUuid}/files/${f.uuid}/download`, { token })
                if (!res.ok) return
                const blob = await res.blob()
                downloadBlob(blob, f.original_name)
              }}
            >
              Descargar
            </a>
          </li>
        ))}
      </ul>
      {files.length === 0 ? <p className="text-sm text-muted">Sin archivos.</p> : null}
    </Card>
  )
}
