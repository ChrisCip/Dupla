import { zodResolver } from '@hookform/resolvers/zod'
import { useCallback, useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'

import { apiFetch } from '../api/client'
import { Card } from '../components/Card'
import { PrimaryButton } from '../components/PrimaryButton'
import { adminCreateUserSchema, type AdminCreateUserForm } from '../schemas/adminUser'
import { useAuthStore } from '../store/authStore'

type ListedUser = { uuid: string; email: string; role: string }

export function AdminUsersPage() {
  const token = useAuthStore((s) => s.token)
  const [users, setUsers] = useState<ListedUser[]>([])
  const [listError, setListError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [loadingList, setLoadingList] = useState(true)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AdminCreateUserForm>({
    resolver: zodResolver(adminCreateUserSchema),
    defaultValues: {
      email: '',
      password: '',
      role: 'WORKER',
      architectureAccess: true,
    },
  })

  const refresh = useCallback(async () => {
    if (!token) return
    setListError(null)
    const res = await apiFetch('/api/admin/users', { token })
    if (!res.ok) {
      setListError('No se pudo cargar la lista de usuarios')
      return
    }
    setUsers((await res.json()) as ListedUser[])
  }, [token])

  useEffect(() => {
    let cancelled = false
    async function run() {
      setLoadingList(true)
      await refresh()
      if (!cancelled) setLoadingList(false)
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [refresh])

  async function onSubmit(values: AdminCreateUserForm) {
    if (!token) return
    setSubmitError(null)
    const module_ids = values.architectureAccess ? [1] : []
    const res = await apiFetch('/api/admin/users', {
      method: 'POST',
      token,
      body: JSON.stringify({
        email: values.email,
        password: values.password,
        role: values.role,
        module_ids,
      }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      const detail = (body as { detail?: string }).detail
      setSubmitError(detail ?? 'No se pudo crear el usuario')
      return
    }
    reset({
      email: '',
      password: '',
      role: 'WORKER',
      architectureAccess: true,
    })
    await refresh()
  }

  return (
    <>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-ink">Administración de usuarios</h1>
        <p className="mt-2 max-w-prose text-sm text-muted">
          Alta de credenciales, rol y acceso al módulo Arquitectura. Solo usuarios MASTER.
        </p>
      </div>

      <div className="grid gap-10 lg:grid-cols-2 lg:items-start">
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-ink">Crear usuario</h2>
          <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
            <div>
              <label className="du-label" htmlFor="admin-email">
                Correo
              </label>
              <input
                id="admin-email"
                type="email"
                autoComplete="off"
                className="du-input mt-1"
                {...register('email')}
              />
              {errors.email ? <p className="mt-1 text-sm text-primary">{errors.email.message}</p> : null}
            </div>
            <div>
              <label className="du-label" htmlFor="admin-password">
                Contraseña inicial
              </label>
              <input
                id="admin-password"
                type="password"
                autoComplete="new-password"
                className="du-input mt-1"
                {...register('password')}
              />
              {errors.password ? (
                <p className="mt-1 text-sm text-primary">{errors.password.message}</p>
              ) : (
                <p className="du-meta mt-1">Mínimo 8 caracteres. El usuario podrá cambiarla si implementas flujo de reset.</p>
              )}
            </div>
            <div>
              <label className="du-label" htmlFor="admin-role">
                Rol
              </label>
              <select id="admin-role" className="du-input mt-1" {...register('role')}>
                <option value="WORKER">Operario (WORKER)</option>
                <option value="COORDINATOR">Coordinador (COORDINATOR)</option>
                <option value="MASTER">Administrador (MASTER)</option>
              </select>
              {errors.role ? <p className="mt-1 text-sm text-primary">{errors.role.message}</p> : null}
            </div>
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="checkbox" className="rounded border-black/20" {...register('architectureAccess')} />
              Acceso al módulo Arquitectura
            </label>
            {errors.architectureAccess ? (
              <p className="text-sm text-primary">{errors.architectureAccess.message}</p>
            ) : null}
            {submitError ? <p className="text-sm text-primary">{submitError}</p> : null}
            <PrimaryButton type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Creando…' : 'Crear usuario'}
            </PrimaryButton>
          </form>
        </Card>

        <Card className="overflow-hidden p-0">
          <div className="border-b border-black/10 px-4 py-3 text-sm font-semibold text-ink">
            Usuarios registrados
          </div>
          {listError ? <p className="px-4 py-3 text-sm text-primary">{listError}</p> : null}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-black/4 text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Correo</th>
                  <th className="px-4 py-3">Rol</th>
                </tr>
              </thead>
              <tbody>
                {loadingList ? (
                  <tr>
                    <td className="px-4 py-8 text-muted" colSpan={2}>
                      Cargando…
                    </td>
                  </tr>
                ) : null}
                {!loadingList &&
                  users.map((u) => (
                    <tr key={u.uuid} className="border-t border-black/5">
                      <td className="px-4 py-3 text-ink">{u.email}</td>
                      <td className="px-4 py-3 text-muted">{u.role}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </>
  )
}
