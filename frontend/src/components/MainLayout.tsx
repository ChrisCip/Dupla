import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'

import { apiFetch } from '../api/client'
import type { UserRole } from '../constants/userRoles'
import { useChatSync } from '../hooks/useChatSync'
import { useAuthStore } from '../store/authStore'
import { Sidebar } from './Sidebar'

type MeRole = UserRole

export function MainLayout() {
  useChatSync()
  const token = useAuthStore((s) => s.token)
  const userUuid = useAuthStore((s) => s.userUuid)
  const email = useAuthStore((s) => s.email)
  const role = useAuthStore((s) => s.role)
  const setSession = useAuthStore((s) => s.setSession)
  const logout = useAuthStore((s) => s.logout)
  const [unreadNotifs, setUnreadNotifs] = useState(0)

  useEffect(() => {
    if (!token) return
    let cancelled = false
    void (async () => {
      const res = await apiFetch('/api/me/notifications?unread_only=true', { token })
      if (!res.ok || cancelled) return
      const rows = (await res.json()) as unknown[]
      if (!cancelled) setUnreadNotifs(rows.length)
    })()
    return () => {
      cancelled = true
    }
  }, [token])

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
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="border-b border-black/10 bg-white">
          <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-4">
            <div className="du-meta">
              <span className="text-ink">{email}</span>
              {role ? <span> · {role}</span> : null}
              {unreadNotifs > 0 ? (
                <span className="ml-2 rounded-full bg-primary/15 px-2 py-0.5 text-xs font-medium text-primary">
                  {unreadNotifs} aviso{unreadNotifs === 1 ? '' : 's'}
                </span>
              ) : null}
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
        <main className="mx-auto flex min-h-0 w-full max-w-6xl flex-1 flex-col overflow-hidden px-6 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
