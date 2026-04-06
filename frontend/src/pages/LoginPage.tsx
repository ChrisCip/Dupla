import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { AppShell } from '../components/AppShell'
import { Card } from '../components/Card'
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
      navigate('/app/projects', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppShell
      header={
        <header className="border-b border-black/10 bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
            <div className="text-xl font-bold tracking-tight text-primary">GRUPO DUPLA</div>
            <div className="text-sm text-muted">Módulo Arquitectura</div>
          </div>
        </header>
      }
    >
      <div className="grid gap-10 md:grid-cols-2 md:items-start">
        <div>
          <h1 className="text-3xl font-semibold text-ink">Acceso</h1>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Inicia sesión con tu correo corporativo. El token JWT se usa en Swagger y en esta aplicación.
          </p>
        </div>
        <Card className="p-6">
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="du-label" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                className="du-input mt-1"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
                disabled={loading}
              />
            </div>
            <div>
              <label className="du-label" htmlFor="password">
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                className="du-input mt-1"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                disabled={loading}
              />
            </div>
            {error ? <p className="text-sm text-primary">{error}</p> : null}
            <PrimaryButton className="w-full" type="submit" disabled={loading}>
              {loading ? 'Entrando…' : 'Entrar'}
            </PrimaryButton>
          </form>
        </Card>
      </div>
    </AppShell>
  )
}
