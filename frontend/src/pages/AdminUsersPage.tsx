import { useCallback, useEffect, useState } from 'react'

import { apiFetch } from '../api/client'
import { AdminUserImportModal } from '../components/AdminUserImportModal'
import { AdminUserModal } from '../components/AdminUserModal'
import { Card } from '../components/Card'
import { PrimaryButton } from '../components/PrimaryButton'
import { ROLE_LABELS, type UserRole } from '../constants/userRoles'
import { formatPersonFullName } from '../lib/personDisplay'
import { useAuthStore } from '../store/authStore'

type ListedUser = {
  uuid: string
  email: string
  first_name: string
  last_name: string
  role: string
  module_ids: number[]
}

export function AdminUsersPage() {
  const token = useAuthStore((s) => s.token)
  const [users, setUsers] = useState<ListedUser[]>([])
  const [listError, setListError] = useState<string | null>(null)
  const [loadingList, setLoadingList] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create')
  const [editingUser, setEditingUser] = useState<ListedUser | null>(null)

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

  function openCreate() {
    setModalMode('create')
    setEditingUser(null)
    setModalOpen(true)
  }

  function openEdit(u: ListedUser) {
    setModalMode('edit')
    setEditingUser(u)
    setModalOpen(true)
  }

  function closeModal() {
    setModalOpen(false)
    setEditingUser(null)
  }

  function roleLabel(role: string): string {
    return ROLE_LABELS[role as UserRole] ?? role
  }

  return (
    <>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ink md:text-3xl">Usuarios</h1>
          <p className="mt-2 max-w-prose text-sm text-muted">
            Alta y edición de credenciales, rol y acceso al workspace. Solo rol Gerencia.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 shrink-0 self-start">
          <button
            type="button"
            className="rounded-md border border-black/15 px-4 py-2.5 text-sm font-semibold uppercase tracking-wide text-ink hover:bg-black/4"
            onClick={() => setImportModalOpen(true)}
          >
            Importar usuarios
          </button>
          <PrimaryButton type="button" onClick={openCreate}>
            Nuevo usuario
          </PrimaryButton>
        </div>
      </div>

      <Card className="overflow-hidden p-0">
        <div className="border-b border-black/10 px-4 py-3 text-sm font-semibold text-ink">Usuarios registrados</div>
        {listError ? <p className="px-4 py-3 text-sm text-primary">{listError}</p> : null}
        <div className="overflow-x-auto">
          <table className="w-full table-fixed text-left text-sm">
            <thead className="bg-black/4 text-xs uppercase text-muted">
              <tr>
                <th className="px-4 py-3">Nombre</th>
                <th className="px-4 py-3">Correo</th>
                <th className="w-40 px-4 py-3">Rol</th>
                <th className="w-32 px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loadingList ? (
                <tr>
                  <td className="px-4 py-8 text-muted" colSpan={4}>
                    Cargando…
                  </td>
                </tr>
              ) : null}
              {!loadingList &&
                users.map((u) => (
                  <tr key={u.uuid} className="border-t border-black/5">
                    <td className="truncate px-4 py-3 text-ink">
                      {formatPersonFullName(u.first_name, u.last_name, u.email)}
                    </td>
                    <td className="truncate px-4 py-3 text-muted">{u.email}</td>
                    <td className="px-4 py-3 text-muted">{roleLabel(u.role)}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        className="du-link text-xs font-medium uppercase tracking-wide"
                        onClick={() => openEdit(u)}
                      >
                        Editar
                      </button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </Card>

      {token ? (
        <AdminUserImportModal
          token={token}
          open={importModalOpen}
          onClose={() => setImportModalOpen(false)}
          onImported={() => void refresh()}
        />
      ) : null}

      {token ? (
        <AdminUserModal
          token={token}
          open={modalOpen}
          mode={modalMode}
          user={editingUser}
          onClose={closeModal}
          onSaved={() => void refresh()}
        />
      ) : null}
    </>
  )
}
