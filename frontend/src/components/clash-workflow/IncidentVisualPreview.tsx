import { useEffect, useState } from 'react'

import { apiFetch } from '../../api/client'

const NO_REAL_VISUAL_MSG = 'Visual real no disponible. Revisar anexo técnico.'

function AuthenticatedSvg({ path, token, alt }: { path: string; token: string | null; alt: string }) {
  const [src, setSrc] = useState<string | null>(null)
  useEffect(() => {
    if (!token || !path) return
    let cancelled = false
    let objectUrl: string | null = null
    void (async () => {
      const res = await apiFetch(path, { token })
      if (!res.ok || cancelled) return
      const blob = await res.blob()
      objectUrl = URL.createObjectURL(blob)
      if (!cancelled) setSrc(objectUrl)
    })()
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [path, token])
  if (!src) {
    return <div className="aspect-[2/1] animate-pulse bg-black/[0.04]" aria-hidden />
  }
  return <img src={src} alt={alt} className="block w-full bg-white" loading="lazy" />
}

export type IncidentVisualPreviewProps = {
  token: string | null
  composedFullPageUrl?: string | null
  zoomUrl?: string | null
  hasRealVisual?: boolean
  visualWarnings?: string[]
  title?: string
}

export function IncidentVisualPreview({
  token,
  composedFullPageUrl,
  zoomUrl,
  hasRealVisual,
  visualWarnings = [],
  title,
}: IncidentVisualPreviewProps) {
  const alt = title ? `Visual ${title}` : 'Visual de incidencia'

  if (hasRealVisual === false) {
    return (
      <div className="space-y-2">
        <div
          className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-950"
          role="status"
        >
          {NO_REAL_VISUAL_MSG}
        </div>
        {visualWarnings.length > 0 ? (
          <p className="text-[10px] text-muted break-words">{visualWarnings.join(' · ')}</p>
        ) : null}
      </div>
    )
  }

  const mainUrl = composedFullPageUrl?.trim() || null
  const insetUrl = zoomUrl?.trim() || null

  if (!mainUrl && !insetUrl) {
    return (
      <div className="flex aspect-[2/1] items-center justify-center rounded-lg border border-black/10 bg-black/[0.02] text-xs text-muted">
        Sin vista SVG para esta incidencia
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {mainUrl ? (
        <div className="overflow-hidden rounded-lg border border-black/10 bg-white">
          <AuthenticatedSvg path={mainUrl} token={token} alt={alt} />
        </div>
      ) : null}
      {insetUrl ? (
        <div className="space-y-1">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">Zoom (inset secundario)</p>
          <div className="max-w-[220px] overflow-hidden rounded-md border border-black/10 bg-white">
            <AuthenticatedSvg path={insetUrl} token={token} alt={`${alt} zoom`} />
          </div>
        </div>
      ) : null}
      {visualWarnings.length > 0 ? (
        <p className="text-[10px] text-muted break-words">{visualWarnings.join(' · ')}</p>
      ) : null}
    </div>
  )
}
