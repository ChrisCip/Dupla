import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Card } from '../components/Card'
import { DuplaLogo } from '../components/DuplaLogo'
import { PrimaryButton } from '../components/PrimaryButton'
import { useAuthStore } from '../store/authStore'

const FEATURES = [
  'Proyectos y workspace con datos técnicos centralizados',
  'Chat por canal general, mensajes directos y grupos',
  'Tablero de tareas para coordinar el trabajo del equipo',
] as const

export function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
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
    <div className="min-h-screen bg-surface text-ink">
      <div className="grid min-h-screen lg:grid-cols-2">
        <aside className="relative hidden flex-col justify-between overflow-hidden bg-linear-to-br from-[#2c2c2c] via-ink to-[#0d0d0d] px-10 py-12 text-white lg:flex xl:px-14">
          <div
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.12)_1px,transparent_0)] bg-size-[32px_32px] opacity-40"
            aria-hidden
          />
          <div className="relative z-10">
            <DuplaLogo className="h-16 w-auto max-w-[min(100%,360px)] object-contain object-left drop-shadow-sm xl:h-[4.5rem]" />
            <h1 className="mt-10 text-3xl font-semibold leading-[1.15] tracking-tight xl:text-4xl">
              La operación del equipo, centralizada
            </h1>
            <p className="mt-5 max-w-lg text-base leading-relaxed text-white/65">
              Herramienta interna para coordinar proyectos, documentación, comunicación y tareas del
              equipo en un solo entorno seguro.
            </p>
            <ul className="mt-12 space-y-4">
              {FEATURES.map((line) => (
                <li key={line} className="flex gap-3 text-base leading-snug text-white/90">
                  <span
                    className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/35 text-[11px] font-bold text-white"
                    aria-hidden
                  >
                    ✓
                  </span>
                  <span>{line}</span>
                </li>
              ))}
            </ul>
          </div>
          <p className="relative z-10 text-xs text-white/45">
            © {new Date().getFullYear()} Grupo Dupla · Uso exclusivo autorizado
          </p>
        </aside>

        <div className="flex flex-col justify-center px-6 py-12 sm:px-10 lg:px-12 xl:px-16">
          <div className="mx-auto w-full max-w-[420px]">
            <div className="mb-10 flex flex-col items-center lg:hidden">
              <DuplaLogo className="h-14 w-auto max-w-[300px] object-contain" />
            </div>

            <Card className="border-black/10 p-9 shadow-[0_8px_30px_rgba(0,0,0,0.06)] sm:p-10">
              <header className="mb-8">
                <h2 className="text-2xl font-semibold tracking-tight text-ink">Iniciar sesión</h2>
                <p className="du-meta mt-2 leading-relaxed">
                  Introduce el correo y la contraseña que te haya facilitado el administrador.
                </p>
              </header>

              <form onSubmit={onSubmit} className="space-y-5">
                <div>
                  <label className="du-label" htmlFor="login-email">
                    Correo electrónico
                  </label>
                  <input
                    id="login-email"
                    name="email"
                    type="email"
                    inputMode="email"
                    autoComplete="username"
                    placeholder="nombre@empresa.com"
                    className="du-input mt-1.5"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={loading}
                    required
                  />
                </div>
                <div>
                  <label className="du-label" htmlFor="login-password">
                    Contraseña
                  </label>
                  <input
                    id="login-password"
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    placeholder="••••••••"
                    className="du-input mt-1.5"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={loading}
                    required
                  />
                </div>

                {error ? (
                  <p
                    className="rounded-lg border border-primary/25 bg-primary/5 px-3 py-2.5 text-sm text-primary"
                    role="alert"
                  >
                    {error}
                  </p>
                ) : null}

                <PrimaryButton className="w-full py-2.5" type="submit" disabled={loading}>
                  {loading ? 'Entrando…' : 'Entrar a la plataforma'}
                </PrimaryButton>
              </form>

              <p className="du-meta mt-8 border-t border-black/10 pt-6 text-center leading-relaxed">
                ¿No tienes cuenta o no puedes entrar? Contacta con el administrador del sistema.
              </p>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
