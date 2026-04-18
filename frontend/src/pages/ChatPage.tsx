import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { Card } from '../components/Card'
import { ChatComposer } from '../components/chat/ChatComposer'
import { ChatConversationSidebar } from '../components/chat/ChatConversationSidebar'
import { ChatMessageList } from '../components/chat/ChatMessageList'
import { PrimaryButton } from '../components/PrimaryButton'
import { useAuthStore } from '../store/authStore'
import { useChatStore } from '../store/chatStore'
import type { ChatConversationSummary, ChatMessage } from '../types/chat'

export function ChatPage() {
  const [searchParams] = useSearchParams()
  const token = useAuthStore((s) => s.token)
  const userUuid = useAuthStore((s) => s.userUuid)
  const email = useAuthStore((s) => s.email)
  const conversations = useChatStore((s) => s.conversations)
  const activeConversationUuid = useChatStore((s) => s.activeConversationUuid)
  const setActiveConversationUuid = useChatStore((s) => s.setActiveConversationUuid)
  const setConversations = useChatStore((s) => s.setConversations)
  const messages = useChatStore((s) => s.messages)
  const setMessages = useChatStore((s) => s.setMessages)
  const appendMessages = useChatStore((s) => s.appendMessages)
  const directory = useChatStore((s) => s.directory)
  const setDirectory = useChatStore((s) => s.setDirectory)

  const [draft, setDraft] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const [showDm, setShowDm] = useState(false)
  const [showGroup, setShowGroup] = useState(false)
  const [dmTarget, setDmTarget] = useState('')
  const [groupTitle, setGroupTitle] = useState('')
  const [groupMemberSearch, setGroupMemberSearch] = useState('')
  const [groupSelectedUuids, setGroupSelectedUuids] = useState<string[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  const refreshConversations = useCallback(async () => {
    if (!token) return
    const res = await apiFetch('/api/chat/conversations', { token })
    if (res.ok) {
      setConversations((await res.json()) as ChatConversationSummary[])
    }
  }, [token, setConversations])

  useEffect(() => {
    if (!token) return
    let cancelled = false
    async function run() {
      const res = await apiFetch('/api/chat/directory', { token })
      if (!res.ok || cancelled) return
      setDirectory((await res.json()) as { uuid: string; email: string }[])
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [token, setDirectory])

  useEffect(() => {
    const fromUrl = searchParams.get('conversation')
    if (fromUrl && token) {
      setActiveConversationUuid(fromUrl)
      void refreshConversations()
    }
  }, [searchParams, token, setActiveConversationUuid, refreshConversations])

  useEffect(() => {
    if (!token || conversations.length === 0) return
    if (activeConversationUuid) return
    const general = conversations.find((c) => c.kind === 'GENERAL') ?? conversations[0]
    setActiveConversationUuid(general.uuid)
  }, [token, conversations, activeConversationUuid, setActiveConversationUuid])

  useEffect(() => {
    if (!token || !activeConversationUuid) return
    let cancelled = false
    const conv = activeConversationUuid
    setMessages([])
    async function load() {
      const res = await apiFetch(`/api/chat/conversations/${conv}/messages`, { token })
      if (!res.ok || cancelled) return
      if (useChatStore.getState().activeConversationUuid !== conv) return
      setMessages((await res.json()) as ChatMessage[])
      void refreshConversations()
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [token, activeConversationUuid, setMessages, refreshConversations])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, activeConversationUuid])

  async function openDirect() {
    if (!token || !dmTarget) return
    setError(null)
    const res = await apiFetch('/api/chat/conversations/direct', {
      method: 'POST',
      token,
      body: JSON.stringify({ user_uuid: dmTarget }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      setError((body as { detail?: string }).detail ?? 'No se pudo abrir el chat')
      return
    }
    const row = (await res.json()) as ChatConversationSummary
    await refreshConversations()
    setActiveConversationUuid(row.uuid)
    setShowDm(false)
    setDmTarget('')
  }

  async function createGroup() {
    if (!token) return
    const uuids = groupSelectedUuids
    if (!groupTitle.trim() || uuids.length < 1) {
      setError('Indica nombre del grupo y al menos un miembro.')
      return
    }
    setError(null)
    const res = await apiFetch('/api/chat/conversations/group', {
      method: 'POST',
      token,
      body: JSON.stringify({ title: groupTitle.trim(), member_uuids: uuids }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      setError((body as { detail?: string }).detail ?? 'No se pudo crear el grupo')
      return
    }
    const row = (await res.json()) as ChatConversationSummary
    await refreshConversations()
    setActiveConversationUuid(row.uuid)
    setShowGroup(false)
    setGroupTitle('')
    setGroupMemberSearch('')
    setGroupSelectedUuids([])
  }

  const groupPickerCandidates = useMemo(() => {
    const q = groupMemberSearch.trim().toLowerCase()
    const selected = new Set(groupSelectedUuids)
    return directory
      .filter((u) => !selected.has(u.uuid))
      .filter((u) => q === '' || u.email.toLowerCase().includes(q))
      .slice(0, 50)
  }, [directory, groupMemberSearch, groupSelectedUuids])

  function addGroupMember(uuid: string) {
    setGroupSelectedUuids((prev) => (prev.includes(uuid) ? prev : [...prev, uuid]))
    setGroupMemberSearch('')
  }

  function removeGroupMember(uuid: string) {
    setGroupSelectedUuids((prev) => prev.filter((id) => id !== uuid))
  }

  const send = useCallback(async () => {
    const text = draft.trim()
    if (!token || !text || !activeConversationUuid || !userUuid) return
    setError(null)
    const optimisticUuid = `optimistic-${crypto.randomUUID()}`
    const optimistic: ChatMessage = {
      uuid: optimisticUuid,
      conversation_uuid: activeConversationUuid,
      body: text,
      created_at: new Date().toISOString(),
      author: { uuid: userUuid, email: email ?? '' },
    }
    appendMessages([optimistic])
    setDraft('')
    setSending(true)
    try {
      const res = await apiFetch(`/api/chat/conversations/${activeConversationUuid}/messages`, {
        method: 'POST',
        token,
        body: JSON.stringify({ body: text }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setError((body as { detail?: string }).detail ?? 'No se pudo enviar')
        const prev = useChatStore.getState().messages
        setMessages(prev.filter((m) => m.uuid !== optimisticUuid))
        setDraft(text)
        return
      }
      const msg = (await res.json()) as ChatMessage
      const prev = useChatStore.getState().messages
      const without = prev.filter((m) => m.uuid !== optimisticUuid)
      setMessages(without.some((m) => m.uuid === msg.uuid) ? without : [...without, msg])
      void refreshConversations()
    } finally {
      setSending(false)
    }
  }, [
    token,
    draft,
    activeConversationUuid,
    userUuid,
    email,
    appendMessages,
    setMessages,
    refreshConversations,
  ])

  const activeMeta = conversations.find((c) => c.uuid === activeConversationUuid)

  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-ink">Chat interno</h1>
        <p className="mt-2 text-sm text-muted">
          Canal general para avisos del equipo, chats uno a uno y grupos. El menú avisa si hay actividad nueva
          mientras navegas otras secciones.
        </p>
      </div>

      <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
        <ChatConversationSidebar
          conversations={conversations}
          activeConversationUuid={activeConversationUuid}
          onSelect={setActiveConversationUuid}
          onNewChat={() => {
            setError(null)
            setShowDm(true)
          }}
          onNewGroup={() => {
            setError(null)
            setGroupTitle('')
            setGroupMemberSearch('')
            setGroupSelectedUuids([])
            setShowGroup(true)
          }}
        />

        <Card className="flex min-h-[min(70vh,560px)] min-w-0 flex-1 flex-col overflow-hidden p-0">
          <div className="border-b border-black/10 bg-black/2 px-4 py-3">
            <h2 className="text-base font-semibold text-ink">
              {activeMeta?.display_title ?? 'Chat'}
            </h2>
            {activeMeta ? (
              <p className="du-meta mt-1">
                {activeMeta.kind === 'GENERAL' && 'Mensajes visibles para todo el equipo.'}
                {activeMeta.kind === 'DIRECT' && 'Chat directo entre dos personas.'}
                {activeMeta.kind === 'GROUP' &&
                  (activeMeta.participant_count != null
                    ? `Grupo · ${activeMeta.participant_count} personas`
                    : 'Grupo')}
                {activeMeta.kind === 'PROJECT' && 'Chat vinculado al proyecto.'}
              </p>
            ) : null}
          </div>
          {!activeConversationUuid ? (
            <div className="flex flex-1 items-center justify-center px-4 py-8">
              <p className="text-sm text-muted">Cargando conversaciones…</p>
            </div>
          ) : (
            <div className="flex min-h-0 flex-1 flex-col">
              {messages.length === 0 ? (
                <div className="flex flex-1 items-center justify-center px-4 py-8">
                  <p className="text-sm text-muted">Aún no hay mensajes. Escribe el primero.</p>
                </div>
              ) : (
                <ChatMessageList messages={messages} userUuid={userUuid} bottomRef={bottomRef} />
              )}
              <ChatComposer
                value={draft}
                onChange={setDraft}
                onSend={send}
                disabled={!activeConversationUuid}
                sending={sending}
                error={error}
              />
            </div>
          )}
        </Card>
      </div>

      {showDm ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) {
              setError(null)
              setShowDm(false)
            }
          }}
        >
          <div
            className="w-full max-w-md rounded-lg border border-black/10 bg-white p-6 shadow-lg"
            role="dialog"
            aria-modal="true"
            aria-labelledby="dm-modal-title"
          >
            <h2 id="dm-modal-title" className="text-lg font-semibold text-ink">
              Chat con una persona
            </h2>
            <p className="du-meta mt-1">Se abre un hilo privado entre tú y la persona elegida.</p>
            <label className="du-label mt-4 block" htmlFor="dm-user">
              Usuario
            </label>
            <select
              id="dm-user"
              className="du-input mt-1 w-full"
              value={dmTarget}
              onChange={(e) => setDmTarget(e.target.value)}
            >
              <option value="">Selecciona…</option>
              {directory.map((u) => (
                <option key={u.uuid} value={u.uuid}>
                  {u.email}
                </option>
              ))}
            </select>
            {error ? <p className="mt-2 text-sm text-primary">{error}</p> : null}
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-md px-3 py-2 text-sm text-muted hover:text-ink"
                onClick={() => {
                  setError(null)
                  setShowDm(false)
                }}
              >
                Cancelar
              </button>
              <PrimaryButton type="button" disabled={!dmTarget} onClick={() => void openDirect()}>
                Abrir chat
              </PrimaryButton>
            </div>
          </div>
        </div>
      ) : null}

      {showGroup ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) {
              setError(null)
              setGroupTitle('')
              setGroupMemberSearch('')
              setGroupSelectedUuids([])
              setShowGroup(false)
            }
          }}
        >
          <div
            className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-lg border border-black/10 bg-white p-6 shadow-lg"
            role="dialog"
            aria-modal="true"
            aria-labelledby="group-modal-title"
          >
            <h2 id="group-modal-title" className="text-lg font-semibold text-ink">
              Nuevo grupo
            </h2>
            <p className="du-meta mt-1">Tú quedas incluido automáticamente. Elige al menos un miembro más.</p>
            <label className="du-label mt-4 block" htmlFor="group-title">
              Nombre del grupo
            </label>
            <input
              id="group-title"
              className="du-input mt-1 w-full"
              value={groupTitle}
              onChange={(e) => setGroupTitle(e.target.value)}
              maxLength={120}
            />
            <div className="du-label mt-4">Miembros</div>
            <p className="mt-1 text-xs text-muted">
              Busca por correo y elige de la lista para añadir. Puedes quitar miembros con la ×.
            </p>
            <label className="du-label mt-3 block" htmlFor="group-member-search">
              Buscar usuario
            </label>
            <input
              id="group-member-search"
              type="search"
              autoComplete="off"
              className="du-input mt-1 w-full"
              placeholder="Escribe para filtrar…"
              value={groupMemberSearch}
              onChange={(e) => setGroupMemberSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && groupPickerCandidates[0]) {
                  e.preventDefault()
                  addGroupMember(groupPickerCandidates[0].uuid)
                }
              }}
            />
            {groupSelectedUuids.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {groupSelectedUuids.map((id) => {
                  const label = directory.find((u) => u.uuid === id)?.email ?? id
                  return (
                    <span
                      key={id}
                      className="inline-flex max-w-full items-center gap-1 rounded-full border border-primary/30 bg-primary/[0.08] py-1 pl-2.5 pr-1 text-xs text-ink"
                    >
                      <span className="truncate">{label}</span>
                      <button
                        type="button"
                        className="shrink-0 rounded-full px-1.5 py-0.5 text-muted hover:bg-black/10 hover:text-ink"
                        aria-label={`Quitar ${label}`}
                        onClick={() => removeGroupMember(id)}
                      >
                        ×
                      </button>
                    </span>
                  )
                })}
              </div>
            ) : (
              <p className="mt-2 text-xs text-muted">Nadie añadido aún.</p>
            )}
            <div className="du-label mt-3">Resultados</div>
            <ul
              className="mt-1 max-h-48 overflow-y-auto rounded-md border border-black/10 bg-white p-1 shadow-inner"
              role="listbox"
              aria-label="Usuarios disponibles"
            >
              {groupPickerCandidates.length === 0 ? (
                <li className="px-2 py-3 text-center text-sm text-muted">
                  {directory.length === 0
                    ? 'No hay usuarios en el directorio.'
                    : 'Sin coincidencias o todos ya están en el grupo.'}
                </li>
              ) : (
                groupPickerCandidates.map((u) => (
                  <li key={u.uuid}>
                    <button
                      type="button"
                      role="option"
                      className="w-full rounded px-2 py-2 text-left text-sm text-ink hover:bg-primary/[0.08]"
                      onClick={() => addGroupMember(u.uuid)}
                    >
                      {u.email}
                    </button>
                  </li>
                ))
              )}
            </ul>
            {error ? <p className="mt-2 text-sm text-primary">{error}</p> : null}
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-md px-3 py-2 text-sm text-muted hover:text-ink"
                onClick={() => {
                  setError(null)
                  setGroupTitle('')
                  setGroupMemberSearch('')
                  setGroupSelectedUuids([])
                  setShowGroup(false)
                }}
              >
                Cancelar
              </button>
              <PrimaryButton type="button" onClick={() => void createGroup()}>
                Crear grupo
              </PrimaryButton>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
