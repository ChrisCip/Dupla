const base = import.meta.env.VITE_API_BASE ?? ''

export function apiUrl(path: string): string {
  if (path.startsWith('http')) return path
  const p = path.startsWith('/') ? path : `/${path}`
  return `${base}${p}`
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
  return fetch(apiUrl(path), { ...rest, headers: h })
}
