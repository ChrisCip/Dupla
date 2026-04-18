import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'

import { apiFetch } from '../api/client'
import { ROLE_LABELS, USER_ROLES, type UserRole } from '../constants/userRoles'
import { PrimaryButton } from './PrimaryButton'
import {
  adminCreateUserSchema,
  adminEditUserSchema,
  type AdminCreateUserForm,
  type AdminEditUserForm,
} from '../schemas/adminUser'

type ListedUser = {
  uuid: string
  email: string
  first_name: string
  last_name: string
  role: string
  module_ids: number[]
}

type Props = {
  token: string
  open: boolean
  mode: 'create' | 'edit'
  user: ListedUser | null
  onClose: () => void
  onSaved: () => void
}

export function AdminUserModal({ token, open, mode, user, onClose, onSaved }: Props) {
  const createForm = useForm<AdminCreateUserForm>({
    resolver: zodResolver(adminCreateUserSchema),
    defaultValues: {
      first_name: '',
      last_name: '',
      email: '',
      password: '',
      role: 'ARQUITECTURA',
      architectureAccess: true,
    },
  })

  const editForm = useForm<AdminEditUserForm>({
    resolver: zodResolver(adminEditUserSchema),
    defaultValues: {
      first_name: '',
      last_name: '',
      email: '',
      password: '',
      role: 'ARQUITECTURA',
      architectureAccess: true,
    },
  })

  useEffect(() => {
    if (!open) return
    if (mode === 'edit' && user) {
      const hasArch = user.module_ids?.includes(1) ?? true
      editForm.reset({
        first_name: user.first_name,
        last_name: user.last_name,
        email: user.email,
        password: '',
        role: user.role as UserRole,
        architectureAccess: hasArch,
      })
    }
    if (mode === 'create') {
      createForm.reset({
        first_name: '',
        last_name: '',
        email: '',
        password: '',
        role: 'ARQUITECTURA',
        architectureAccess: true,
      })
    }
  }, [open, mode, user, createForm, editForm])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  async function submitCreate(values: AdminCreateUserForm) {
    const module_ids = values.architectureAccess ? [1] : []
    const res = await apiFetch('/api/admin/users', {
      method: 'POST',
      token,
      body: JSON.stringify({
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        password: values.password,
        role: values.role,
        module_ids,
      }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      createForm.setError('root', {
        message: (body as { detail?: string }).detail ?? 'No se pudo crear el usuario',
      })
      return
    }
    onSaved()
    onClose()
  }

  async function submitEdit(values: AdminEditUserForm) {
    if (!user) return
    const module_ids = values.architectureAccess ? [1] : []
    const body: Record<string, unknown> = {
      first_name: values.first_name,
      last_name: values.last_name,
      email: values.email,
      role: values.role,
      module_ids,
    }
    if (values.password.trim().length > 0) {
      body.password = values.password
    }
    const res = await apiFetch(`/api/admin/users/${user.uuid}`, {
      method: 'PATCH',
      token,
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const j = await res.json().catch(() => ({}))
      editForm.setError('root', {
        message: (j as { detail?: string }).detail ?? 'No se pudo guardar',
      })
      return
    }
    onSaved()
    onClose()
  }

  if (!open) return null

  const isCreate = mode === 'create'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-black/10 bg-white p-6 shadow-lg"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-user-modal-title"
      >
        <h2 id="admin-user-modal-title" className="text-lg font-semibold text-ink">
          {isCreate ? 'Nuevo usuario' : 'Editar usuario'}
        </h2>

        {isCreate ? (
          <form className="mt-6 space-y-4" onSubmit={createForm.handleSubmit(submitCreate)} noValidate>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="du-label" htmlFor="um-first">
                  Nombre
                </label>
                <input
                  id="um-first"
                  type="text"
                  autoComplete="given-name"
                  className="du-input mt-1"
                  {...createForm.register('first_name')}
                />
                {createForm.formState.errors.first_name ? (
                  <p className="mt-1 text-sm text-primary">{createForm.formState.errors.first_name.message}</p>
                ) : null}
              </div>
              <div>
                <label className="du-label" htmlFor="um-last">
                  Apellido
                </label>
                <input
                  id="um-last"
                  type="text"
                  autoComplete="family-name"
                  className="du-input mt-1"
                  {...createForm.register('last_name')}
                />
                {createForm.formState.errors.last_name ? (
                  <p className="mt-1 text-sm text-primary">{createForm.formState.errors.last_name.message}</p>
                ) : null}
              </div>
            </div>
            <div>
              <label className="du-label" htmlFor="um-email">
                Correo
              </label>
              <input id="um-email" type="email" autoComplete="off" className="du-input mt-1" {...createForm.register('email')} />
              {createForm.formState.errors.email ? (
                <p className="mt-1 text-sm text-primary">{createForm.formState.errors.email.message}</p>
              ) : null}
            </div>
            <div>
              <label className="du-label" htmlFor="um-password">
                Contraseña inicial
              </label>
              <input
                id="um-password"
                type="password"
                autoComplete="new-password"
                className="du-input mt-1"
                {...createForm.register('password')}
              />
              {createForm.formState.errors.password ? (
                <p className="mt-1 text-sm text-primary">{createForm.formState.errors.password.message}</p>
              ) : (
                <p className="du-meta mt-1">Mínimo 8 caracteres.</p>
              )}
            </div>
            <div>
              <label className="du-label" htmlFor="um-role">
                Rol
              </label>
              <select id="um-role" className="du-input mt-1" {...createForm.register('role')}>
                {USER_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {ROLE_LABELS[r]}
                  </option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="checkbox" className="rounded border-black/20" {...createForm.register('architectureAccess')} />
              Acceso a proyectos y workspace
            </label>
            {createForm.formState.errors.root ? (
              <p className="text-sm text-primary">{createForm.formState.errors.root.message}</p>
            ) : null}
            <div className="flex flex-wrap justify-end gap-2 pt-2">
              <button type="button" className="rounded-md px-3 py-2 text-sm text-muted hover:text-ink" onClick={onClose}>
                Cancelar
              </button>
              <PrimaryButton type="submit" disabled={createForm.formState.isSubmitting}>
                {createForm.formState.isSubmitting ? 'Creando…' : 'Crear usuario'}
              </PrimaryButton>
            </div>
          </form>
        ) : (
          <form className="mt-6 space-y-4" onSubmit={editForm.handleSubmit(submitEdit)} noValidate>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="du-label" htmlFor="ue-first">
                  Nombre
                </label>
                <input
                  id="ue-first"
                  type="text"
                  autoComplete="given-name"
                  className="du-input mt-1"
                  {...editForm.register('first_name')}
                />
                {editForm.formState.errors.first_name ? (
                  <p className="mt-1 text-sm text-primary">{editForm.formState.errors.first_name.message}</p>
                ) : null}
              </div>
              <div>
                <label className="du-label" htmlFor="ue-last">
                  Apellido
                </label>
                <input
                  id="ue-last"
                  type="text"
                  autoComplete="family-name"
                  className="du-input mt-1"
                  {...editForm.register('last_name')}
                />
                {editForm.formState.errors.last_name ? (
                  <p className="mt-1 text-sm text-primary">{editForm.formState.errors.last_name.message}</p>
                ) : null}
              </div>
            </div>
            <div>
              <label className="du-label" htmlFor="ue-email">
                Correo
              </label>
              <input id="ue-email" type="email" className="du-input mt-1" {...editForm.register('email')} />
              {editForm.formState.errors.email ? (
                <p className="mt-1 text-sm text-primary">{editForm.formState.errors.email.message}</p>
              ) : null}
            </div>
            <div>
              <label className="du-label" htmlFor="ue-password">
                Nueva contraseña <span className="font-normal text-muted">(opcional)</span>
              </label>
              <input
                id="ue-password"
                type="password"
                autoComplete="new-password"
                className="du-input mt-1"
                placeholder="Dejar vacío para no cambiar"
                {...editForm.register('password')}
              />
              {editForm.formState.errors.password ? (
                <p className="mt-1 text-sm text-primary">{editForm.formState.errors.password.message}</p>
              ) : null}
            </div>
            <div>
              <label className="du-label" htmlFor="ue-role">
                Rol
              </label>
              <select id="ue-role" className="du-input mt-1" {...editForm.register('role')}>
                {USER_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {ROLE_LABELS[r]}
                  </option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="checkbox" className="rounded border-black/20" {...editForm.register('architectureAccess')} />
              Acceso a proyectos y workspace
            </label>
            {editForm.formState.errors.root ? (
              <p className="text-sm text-primary">{editForm.formState.errors.root.message}</p>
            ) : null}
            <div className="flex flex-wrap justify-end gap-2 pt-2">
              <button type="button" className="rounded-md px-3 py-2 text-sm text-muted hover:text-ink" onClick={onClose}>
                Cancelar
              </button>
              <PrimaryButton type="submit" disabled={editForm.formState.isSubmitting}>
                {editForm.formState.isSubmitting ? 'Guardando…' : 'Guardar cambios'}
              </PrimaryButton>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
