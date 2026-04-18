import { useEffect } from 'react'
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
  const setSession = useAuthStore((s) => s.setSession)

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
        <main className="mx-auto flex min-h-0 w-full max-w-6xl flex-1 flex-col overflow-hidden px-4 py-4 sm:px-5 sm:py-5 md:px-6 md:py-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
