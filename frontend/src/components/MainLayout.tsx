import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { useChatSync } from '../hooks/useChatSync'
import { useAuthStore } from '../store/authStore'
import { Sidebar } from './Sidebar'

type MeRole = 'MASTER' | 'COORDINATOR' | 'WORKER'

export function MainLayout() {
  useChatSync()
  const token = useAuthStore((s) => s.token)
  const userUuid = useAuthStore((s) => s.userUuid)
  const email = useAuthStore((s) => s.email)
  const role = useAuthStore((s) => s.role)
  const setSession = useAuthStore((s) => s.setSession)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    if (!token || userUuid) return
    void (async () => {
      const res = await apiFetch('/api/me', { token })
      if (!res.ok) return
      const p = (await res.json()) as { uuid: string; email: string; role: MeRole }
      setSession(token, p.email, p.role, p.uuid)
    })()
  }, [token, userUuid, setSession])

  return (
    <div className="flex min-h-screen bg-surface text-ink">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-black/10 bg-white">
          <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-4">
            <div className="du-meta">
              <span className="text-ink">{email}</span>
              {role ? <span> · {role}</span> : null}
            </div>
            <button
              type="button"
              className="text-sm text-muted underline-offset-4 transition hover:text-ink focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              onClick={() => logout()}
            >
              Salir
            </button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
