import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { PrimaryButton } from '../components/PrimaryButton'
import { useAuthStore } from '../store/authStore'

export function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const [email, setEmail] = useState('master@dupla.demo')
  const [password, setPassword] = useState('master123')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      navigate('/app', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-black/5">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
          <div className="text-xl font-bold tracking-tight text-primary">GRUPO DUPLA</div>
          <div className="text-sm text-muted">Módulo Arquitectura</div>
        </div>
      </header>
      <main className="mx-auto grid max-w-5xl gap-10 px-6 py-14 md:grid-cols-2 md:items-start">
        <div>
          <h1 className="text-3xl font-semibold text-ink">Acceso</h1>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Inicia sesión con tu correo corporativo. El token JWT se usa en Swagger y en esta aplicación.
          </p>
        </div>
        <form onSubmit={onSubmit} className="rounded-xl border border-black/10 bg-white p-6 shadow-sm">
          <label className="block text-sm font-medium text-ink" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            className="mt-1 w-full rounded-md border border-black/15 px-3 py-2 text-sm outline-none focus:border-primary"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
          />
          <label className="mt-4 block text-sm font-medium text-ink" htmlFor="password">
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            className="mt-1 w-full rounded-md border border-black/15 px-3 py-2 text-sm outline-none focus:border-primary"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
          {error ? <p className="mt-3 text-sm text-primary">{error}</p> : null}
          <PrimaryButton className="mt-6 w-full" type="submit" disabled={loading}>
            {loading ? 'Entrando…' : 'Entrar'}
          </PrimaryButton>
        </form>
      </main>
    </div>
  )
}
