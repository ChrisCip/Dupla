import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { PrimaryButton } from '../components/PrimaryButton'
import { useAuthStore } from '../store/authStore'

type Project = { uuid: string; name: string; client_name: string | null; status: string }

export function DashboardPage() {
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)
  const email = useAuthStore((s) => s.email)
  const role = useAuthStore((s) => s.role)
  const [projects, setProjects] = useState<Project[]>([])
  const [name, setName] = useState('Nuevo proyecto')
  const [client, setClient] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    if (!token) return
    const res = await apiFetch('/api/projects', { token })
    if (!res.ok) {
      setError('No se pudieron cargar proyectos')
      return
    }
    setProjects((await res.json()) as Project[])
  }

  useEffect(() => {
    void refresh()
  }, [token])

  async function createProject(e: React.FormEvent) {
    e.preventDefault()
    if (!token) return
    setError(null)
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
  }

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-black/5">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div>
            <div className="text-xl font-bold tracking-tight text-primary">GRUPO DUPLA</div>
            <div className="text-xs text-muted">
              {email} · {role}
            </div>
          </div>
          <button
            type="button"
            className="text-sm text-muted underline-offset-4 hover:underline"
            onClick={() => logout()}
          >
            Salir
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-ink">Proyectos</h1>
            <p className="mt-2 max-w-prose text-sm text-muted">
              Crea un proyecto y abre el workspace para armar tiradas/planos/fases con ítems y precios.
            </p>
          </div>
          <form onSubmit={createProject} className="w-full max-w-md rounded-xl border border-black/10 p-4">
            <div className="text-sm font-medium text-ink">Nuevo proyecto</div>
            <input
              className="mt-2 w-full rounded-md border border-black/15 px-3 py-2 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <input
              className="mt-2 w-full rounded-md border border-black/15 px-3 py-2 text-sm"
              placeholder="Cliente (opcional)"
              value={client}
              onChange={(e) => setClient(e.target.value)}
            />
            {error ? <p className="mt-2 text-sm text-primary">{error}</p> : null}
            <PrimaryButton className="mt-3 w-full" type="submit">
              Crear
            </PrimaryButton>
          </form>
        </div>

        <div className="mt-10 overflow-hidden rounded-xl border border-black/10">
          <table className="w-full text-left text-sm">
            <thead className="bg-black/[0.02] text-xs uppercase text-muted">
              <tr>
                <th className="px-4 py-3">Nombre</th>
                <th className="px-4 py-3">Cliente</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.uuid} className="border-t border-black/5">
                  <td className="px-4 py-3 font-medium text-ink">{p.name}</td>
                  <td className="px-4 py-3 text-muted">{p.client_name ?? '—'}</td>
                  <td className="px-4 py-3 text-muted">{p.status}</td>
                  <td className="px-4 py-3 text-right">
                    <Link className="text-sm font-semibold text-primary" to={`/app/projects/${p.uuid}`}>
                      Abrir
                    </Link>
                  </td>
                </tr>
              ))}
              {projects.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-sm text-muted" colSpan={4}>
                    No hay proyectos todavía.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}
