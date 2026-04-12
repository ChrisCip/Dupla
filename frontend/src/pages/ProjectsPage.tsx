import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { Card } from '../components/Card'
import { PrimaryButton } from '../components/PrimaryButton'
import { WORKFLOW_PHASE_LABELS } from '../constants/workflowPhases'
import type { Project } from '../types/project'
import { useAuthStore } from '../store/authStore'

export function ProjectsPage() {
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.token)
  const role = useAuthStore((s) => s.role)
  const [projects, setProjects] = useState<Project[]>([])
  const [name, setName] = useState('Nuevo proyecto')
  const [client, setClient] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loadingList, setLoadingList] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)
  const feedbackClearRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const refresh = useCallback(async () => {
    if (!token) return
    setError(null)
    const res = await apiFetch('/api/projects', { token })
    if (!res.ok) {
      setError('No se pudieron cargar proyectos')
      return
    }
    setProjects((await res.json()) as Project[])
  }, [token])

  useEffect(() => {
    let cancelled = false
    async function run() {
      setLoadingList(true)
      await refresh()
      if (!cancelled) setLoadingList(false)
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [refresh])

  useEffect(() => {
    return () => {
      if (feedbackClearRef.current) clearTimeout(feedbackClearRef.current)
    }
  }, [])

  async function createProject(e: React.FormEvent) {
    e.preventDefault()
    if (!token) return
    setError(null)
    setSubmitting(true)
    try {
      const res = await apiFetch('/api/projects', {
        method: 'POST',
        token,
        body: JSON.stringify({ name, client_name: client || null }),
      })
      if (!res.ok) {
        setError('No se pudo crear el proyecto')
        return
      }
      setFeedback('Proyecto creado. Ábrelo en la tabla (fila o enlace) o crea otro.')
      if (feedbackClearRef.current) clearTimeout(feedbackClearRef.current)
      feedbackClearRef.current = setTimeout(() => setFeedback(null), 6000)
      setName('Nuevo proyecto')
      setClient('')
      await refresh()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <div
        className="sr-only"
        aria-live="polite"
        aria-atomic="true"
      >
        {feedback ?? ''}
      </div>
      {feedback ? (
        <div
          className="du-callout mb-6 flex flex-wrap items-center justify-between gap-3 border-primary/25"
          role="status"
        >
          <span>{feedback}</span>
          <button
            type="button"
            className="du-link text-xs uppercase tracking-wide"
            onClick={() => setFeedback(null)}
          >
            Cerrar
          </button>
        </div>
      ) : null}
      <div className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold text-ink">Proyectos</h1>
          <p className="mt-2 max-w-prose text-sm text-muted">
            Cada proyecto tiene un workspace con flujo por fases, archivos, pliego exportable y materiales.
          </p>
          <ol className="mt-5 max-w-md list-none space-y-2 border-l-2 border-primary/25 pl-4 text-sm text-ink">
            <li>
              <span className="font-semibold text-primary">1.</span>{' '}
              {role === 'MASTER' ? (
                <>
                  Completa el nombre (y el cliente si quieres) y crea el proyecto.
                </>
              ) : (
                <>
                  Solo un administrador crea proyectos; los que te asignen aparecen en la tabla.
                </>
              )}
            </li>
            <li>
              <span className="font-semibold text-primary">2.</span> En la tabla, abre el workspace con un clic en la
              fila o en «Abrir».
            </li>
            <li>
              <span className="font-semibold text-primary">3.</span> Sigue la pestaña <strong>Flujo</strong> y el aviso
              de «siguiente paso» arriba del workspace.
            </li>
          </ol>
        </div>
        {role === 'MASTER' ? (
          <Card className="w-full max-w-md p-4 shadow-md ring-1 ring-black/[0.04]">
            <form onSubmit={createProject} className="space-y-3">
              <div className="text-sm font-semibold text-ink">Nuevo proyecto</div>
              <p className="du-meta leading-relaxed">
                El nombre puede ser el código interno o la obra; el cliente ayuda a filtrar después.
              </p>
              <div>
                <label htmlFor="project-name" className="du-label">
                  Nombre
                </label>
                <input
                  id="project-name"
                  className="du-input mt-1"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  aria-label="Nombre del proyecto"
                  disabled={submitting}
                  required
                />
              </div>
              <div>
                <label htmlFor="project-client" className="du-label">
                  Cliente <span className="font-normal text-muted">(opcional)</span>
                </label>
                <input
                  id="project-client"
                  className="du-input mt-1"
                  placeholder="Ej. Constructora …"
                  value={client}
                  onChange={(e) => setClient(e.target.value)}
                  aria-label="Cliente"
                  disabled={submitting}
                />
              </div>
              {error ? <p className="text-sm font-medium text-primary">{error}</p> : null}
              <PrimaryButton className="w-full" type="submit" disabled={submitting}>
                {submitting ? 'Creando…' : 'Crear proyecto'}
              </PrimaryButton>
            </form>
          </Card>
        ) : (
          <Card className="w-full max-w-md p-4 text-sm text-muted shadow-md ring-1 ring-black/[0.04]">
            <p className="font-medium text-ink">Acceso a proyectos</p>
            <p className="mt-2 leading-relaxed">
              Un administrador debe crear el proyecto y asignarte acceso. Después lo verás en la tabla y podrás abrir el
              workspace, el tablero de tareas y el chat.
            </p>
          </Card>
        )}
      </div>

      <Card className="mt-10 overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-black/4 text-xs uppercase text-muted">
              <tr>
                <th className="px-4 py-3">Nombre</th>
                <th className="px-4 py-3">Cliente</th>
                <th className="px-4 py-3">Fase</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {loadingList ? (
                <tr>
                  <td className="border-l-4 border-l-primary bg-primary/[0.04] px-4 py-4 text-sm text-muted" colSpan={4}>
                    Cargando lista de proyectos…
                  </td>
                </tr>
              ) : null}
              {!loadingList &&
                projects.map((p) => (
                  <tr
                    key={p.uuid}
                    tabIndex={0}
                    className="cursor-pointer border-t border-black/5 transition-colors duration-150 hover:bg-black/[0.04] focus-visible:bg-black/[0.04] focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-primary/40"
                    onClick={() => navigate(`/app/projects/${p.uuid}`)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        navigate(`/app/projects/${p.uuid}`)
                      }
                    }}
                  >
                    <td className="px-4 py-3 font-medium text-ink">{p.name}</td>
                    <td className="px-4 py-3 text-muted">{p.client_name ?? '—'}</td>
                    <td className="px-4 py-3 text-muted">
                      <span className="rounded-md bg-black/[0.06] px-2 py-0.5 text-xs font-medium text-ink">
                        {WORKFLOW_PHASE_LABELS[p.workflow_phase] ?? p.workflow_phase}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        className="du-link text-sm"
                        to={`/app/projects/${p.uuid}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        Abrir workspace →
                      </Link>
                    </td>
                  </tr>
                ))}
              {!loadingList && projects.length === 0 ? (
                <tr>
                  <td className="px-4 py-10" colSpan={4}>
                    <div className="mx-auto max-w-md rounded-lg border border-dashed border-black/15 bg-black/[0.02] px-6 py-8 text-center">
                      <p className="text-sm font-medium text-ink">Todavía no hay proyectos</p>
                      <p className="mt-2 text-sm text-muted">
                        {role === 'MASTER'
                          ? 'Usa el formulario de la derecha (o arriba en el móvil): nombre obligatorio, cliente opcional. Después el proyecto aparece aquí para abrir el workspace.'
                          : 'Cuando un administrador te dé acceso, el proyecto aparecerá aquí.'}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  )
}
