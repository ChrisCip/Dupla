import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { Card } from '../components/Card'
import { PrimaryButton } from '../components/PrimaryButton'
import type { Project } from '../types/project'
import { useAuthStore } from '../store/authStore'

export function ProjectsPage() {
  const token = useAuthStore((s) => s.token)
  const [projects, setProjects] = useState<Project[]>([])
  const [name, setName] = useState('Nuevo proyecto')
  const [client, setClient] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loadingList, setLoadingList] = useState(true)
  const [submitting, setSubmitting] = useState(false)

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
      setName('Nuevo proyecto')
      setClient('')
      await refresh()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <div className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Proyectos</h1>
          <p className="mt-2 max-w-prose text-sm text-muted">
            Crea un proyecto y abre el workspace para armar tiradas, planos y fases con ítems y precios.
          </p>
        </div>
        <Card className="w-full max-w-md p-4">
          <form onSubmit={createProject} className="space-y-3">
            <div className="text-sm font-medium text-ink">Nuevo proyecto</div>
            <input
              className="du-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-label="Nombre del proyecto"
              disabled={submitting}
              required
            />
            <input
              className="du-input"
              placeholder="Cliente (opcional)"
              value={client}
              onChange={(e) => setClient(e.target.value)}
              aria-label="Cliente"
              disabled={submitting}
            />
            {error ? <p className="text-sm text-primary">{error}</p> : null}
            <PrimaryButton className="w-full" type="submit" disabled={submitting}>
              {submitting ? 'Creando…' : 'Crear proyecto'}
            </PrimaryButton>
          </form>
        </Card>
      </div>

      <Card className="mt-10 overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-black/4 text-xs uppercase text-muted">
              <tr>
                <th className="px-4 py-3">Nombre</th>
                <th className="px-4 py-3">Cliente</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {loadingList ? (
                <tr>
                  <td className="px-4 py-8 text-center text-sm text-muted" colSpan={4}>
                    Cargando…
                  </td>
                </tr>
              ) : null}
              {!loadingList &&
                projects.map((p) => (
                  <tr
                    key={p.uuid}
                    className="border-t border-black/5 transition-colors hover:bg-black/2"
                  >
                    <td className="px-4 py-3 font-medium text-ink">{p.name}</td>
                    <td className="px-4 py-3 text-muted">{p.client_name ?? '—'}</td>
                    <td className="px-4 py-3 text-muted">{p.status}</td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        className="text-sm font-semibold text-primary underline-offset-2 hover:underline"
                        to={`/app/projects/${p.uuid}`}
                      >
                        Abrir
                      </Link>
                    </td>
                  </tr>
                ))}
              {!loadingList && projects.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-sm text-muted" colSpan={4}>
                    No hay proyectos todavía.
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
