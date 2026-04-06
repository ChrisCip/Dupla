import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import { apiFetch } from '../api/client'
import { AUTH_PERSIST_KEY } from './authConstants'

type Role = 'MASTER' | 'COORDINATOR' | 'WORKER'

type AuthState = {
  token: string | null
  email: string | null
  role: Role | null
  userUuid: string | null
  setSession: (token: string, email: string, role: Role, userUuid: string) => void
  logout: () => void
  login: (email: string, password: string) => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      email: null,
      role: null,
      userUuid: null,
      setSession: (token, email, role, userUuid) => set({ token, email, role, userUuid }),
      logout: () => set({ token: null, email: null, role: null, userUuid: null }),
      login: async (email, password) => {
        const body = new URLSearchParams()
        body.set('username', email)
        body.set('password', password)
        const res = await apiFetch('/api/auth/token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: body.toString(),
        })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error((err as { detail?: string }).detail ?? 'Login failed')
        }
        const data = (await res.json()) as { access_token: string }
        const me = await apiFetch('/api/me', { token: data.access_token })
        if (!me.ok) throw new Error('Failed to load profile')
        const profile = (await me.json()) as { uuid: string; email: string; role: Role }
        set({
          token: data.access_token,
          email: profile.email,
          role: profile.role,
          userUuid: profile.uuid,
        })
      },
    }),
    { name: AUTH_PERSIST_KEY },
  ),
)
