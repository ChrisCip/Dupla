import { AUTH_PERSIST_KEY } from '../store/authConstants'

const base = import.meta.env.VITE_API_BASE ?? ''

export function apiUrl(path: string): string {
  if (path.startsWith('http')) return path
  const p = path.startsWith('/') ? path : `/${path}`
  return `${base}${p}`
}

function isAuthTokenRequest(path: string): boolean {
  try {
    const pathname = path.includes('://') ? new URL(path).pathname : path
    return pathname.includes('/api/auth/token')
  } catch {
    return path.includes('/api/auth/token')
  }
}

function handleUnauthorizedSession(path: string): void {
  if (isAuthTokenRequest(path)) return
  try {
    localStorage.removeItem(AUTH_PERSIST_KEY)
  } catch {
    /* ignore */
  }
  if (typeof window === 'undefined') return
  if (window.location.pathname.startsWith('/login')) return
  window.location.assign('/login')
}

export async function apiFetch(
  path: string,
  init: RequestInit & { token?: string | null } = {},
): Promise<Response> {
  const { token, headers, ...rest } = init
  const h = new Headers(headers)
  if (token) {
    h.set('Authorization', `Bearer ${token}`)
  }
  if (!h.has('Content-Type') && rest.body && !(rest.body instanceof FormData)) {
    h.set('Content-Type', 'application/json')
  }
  const res = await fetch(apiUrl(path), { ...rest, headers: h })
  if (res.status === 401) {
    handleUnauthorizedSession(path)
  }
  return res
}
