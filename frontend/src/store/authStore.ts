import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import { apiFetch } from '../api/client'
import type { UserRole } from '../constants/userRoles'
import { AUTH_PERSIST_KEY } from './authConstants'

type Role = UserRole

type AuthState = {
  token: string | null
  email: string | null
  firstName: string | null
  lastName: string | null
  role: Role | null
  userUuid: string | null
  mustChangePassword: boolean
  setSession: (
    token: string,
    email: string,
    role: Role,
    userUuid: string,
    firstName: string,
    lastName: string,
    mustChangePassword?: boolean,
  ) => void
  clearMustChangePassword: () => void
  logout: () => void
  login: (email: string, password: string) => Promise<boolean>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      email: null,
      firstName: null,
      lastName: null,
      role: null,
      userUuid: null,
      mustChangePassword: false,
      setSession: (token, email, role, userUuid, firstName, lastName, mustChangePassword = false) =>
        set({
          token,
          email,
          role,
          userUuid,
          firstName,
          lastName,
          mustChangePassword,
        }),
      clearMustChangePassword: () => set({ mustChangePassword: false }),
      logout: () =>
        set({
          token: null,
          email: null,
          firstName: null,
          lastName: null,
          role: null,
          userUuid: null,
          mustChangePassword: false,
        }),
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
        const data = (await res.json()) as { access_token: string; must_change_password?: boolean }
        const me = await apiFetch('/api/me', { token: data.access_token })
        if (!me.ok) throw new Error('Failed to load profile')
        const profile = (await me.json()) as {
          uuid: string
          email: string
          first_name: string
          last_name: string
          role: Role
          must_change_password?: boolean
        }
        const mustChangePassword = profile.must_change_password ?? data.must_change_password ?? false
        set({
          token: data.access_token,
          email: profile.email,
          firstName: profile.first_name,
          lastName: profile.last_name,
          role: profile.role,
          userUuid: profile.uuid,
          mustChangePassword,
        })
        return mustChangePassword
      },
    }),
    { name: AUTH_PERSIST_KEY },
  ),
)
