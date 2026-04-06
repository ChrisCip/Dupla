import { useEffect, useRef, useState } from 'react'

import { apiFetch } from '../api/client'
import { Card } from '../components/Card'
import { PrimaryButton } from '../components/PrimaryButton'
import { useAuthStore } from '../store/authStore'
import { useChatStore } from '../store/chatStore'
import type { ChatConversationSummary, ChatMessage } from '../types/chat'

export function ChatPage() {
  const token = useAuthStore((s) => s.token)
  const userUuid = useAuthStore((s) => s.userUuid)
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
  const [groupMembers, setGroupMembers] = useState<Record<string, boolean>>({})
  const bottomRef = useRef<HTMLDivElement>(null)

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
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [token, activeConversationUuid, setMessages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, activeConversationUuid])

  async function refreshConversations() {
    if (!token) return
    const res = await apiFetch('/api/chat/conversations', { token })
    if (res.ok) {
      setConversations((await res.json()) as ChatConversationSummary[])
    }
  }

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
    const uuids = Object.entries(groupMembers)
      .filter(([, v]) => v)
      .map(([k]) => k)
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
    setGroupMembers({})
  }

  async function send(e: React.FormEvent) {
    e.preventDefault()
    const text = draft.trim()
    if (!token || !text || !activeConversationUuid) return
    setError(null)
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
        return
      }
      const msg = (await res.json()) as ChatMessage
      appendMessages([msg])
      setDraft('')
      void refreshConversations()
    } finally {
      setSending(false)
    }
  }

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
        <aside className="w-full shrink-0 lg:w-72">
          <Card className="p-4">
            <div className="flex flex-wrap gap-2">
              <PrimaryButton
                type="button"
                className="!px-3 !py-1.5 !text-xs"
                onClick={() => {
                  setError(null)
                  setShowDm(true)
                }}
              >
                Chat con…
              </PrimaryButton>
              <button
                type="button"
                className="rounded-md border border-black/15 bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-ink shadow-sm hover:border-primary/30"
                onClick={() => {
                  setError(null)
                  setShowGroup(true)
                }}
              >
                Nuevo grupo
              </button>
            </div>
            <div className="du-label mt-4">Conversaciones</div>
            <ul className="mt-2 space-y-1">
              {conversations.map((c) => (
                <li key={c.uuid}>
                  <button
                    type="button"
                    onClick={() => setActiveConversationUuid(c.uuid)}
                    className={`w-full rounded-md border px-3 py-2 text-left text-sm transition ${
                      c.uuid === activeConversationUuid
                        ? 'border-primary/40 bg-primary/5 text-ink'
                        : 'border-black/10 bg-white hover:border-primary/25'
                    }`}
                  >
                    <div className="font-medium leading-snug">{c.display_title}</div>
                    <div className="du-meta mt-0.5">
                      {c.kind === 'GENERAL'
                        ? 'Avisos'
                        : c.kind === 'DIRECT'
                          ? 'Directo'
                          : 'Grupo'}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        </aside>

        <Card className="flex min-h-[min(70vh,560px)] min-w-0 flex-1 flex-col overflow-hidden p-0">
          <div className="border-b border-black/10 bg-black/2 px-4 py-3">
            <h2 className="text-sm font-semibold text-ink">{activeMeta?.display_title ?? 'Chat'}</h2>
            {activeMeta?.kind === 'GENERAL' ? (
              <p className="du-meta mt-0.5">Mensajes visibles para todo el equipo.</p>
            ) : null}
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {!activeConversationUuid ? (
              <p className="text-sm text-muted">Cargando conversaciones…</p>
            ) : messages.length === 0 ? (
              <p className="text-sm text-muted">Aún no hay mensajes. Escribe el primero.</p>
            ) : null}
            {messages.map((m) => {
              const mine = userUuid !== null && m.author.uuid === userUuid
              return (
                <div
                  key={m.uuid}
                  className={`flex flex-col rounded-lg border px-3 py-2 text-sm ${
                    mine ? 'ml-8 border-primary/25 bg-primary/5' : 'mr-8 border-black/10 bg-white'
                  }`}
                >
                  <div className="du-meta flex justify-between gap-2">
                    <span className={mine ? 'text-primary' : ''}>{m.author.email}</span>
                    <time dateTime={m.created_at}>
                      {new Date(m.created_at).toLocaleString(undefined, {
                        dateStyle: 'short',
                        timeStyle: 'short',
                      })}
                    </time>
                  </div>
                  <p className="mt-1 whitespace-pre-wrap text-ink">{m.body}</p>
                </div>
              )
            })}
            <div ref={bottomRef} />
          </div>
          <form
            className="border-t border-black/10 bg-black/2 px-4 py-3"
            onSubmit={(e) => void send(e)}
          >
            {error ? <p className="mb-2 text-sm text-primary">{error}</p> : null}
            <label className="du-label sr-only" htmlFor="chat-input">
              Mensaje
            </label>
            <textarea
              id="chat-input"
              className="du-input min-h-[88px] resize-y"
              placeholder="Escribe un mensaje…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={sending || !activeConversationUuid}
              maxLength={4000}
            />
            <div className="mt-2 flex justify-end">
              <PrimaryButton type="submit" disabled={sending || !draft.trim() || !activeConversationUuid}>
                {sending ? 'Enviando…' : 'Enviar'}
              </PrimaryButton>
            </div>
          </form>
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
            <ul className="mt-2 max-h-48 space-y-2 overflow-y-auto rounded-md border border-black/10 p-2">
              {directory.map((u) => (
                <li key={u.uuid}>
                  <label className="flex cursor-pointer items-center gap-2 text-sm text-ink">
                    <input
                      type="checkbox"
                      className="rounded border-black/20"
                      checked={Boolean(groupMembers[u.uuid])}
                      onChange={(e) =>
                        setGroupMembers((prev) => ({ ...prev, [u.uuid]: e.target.checked }))
                      }
                    />
                    {u.email}
                  </label>
                </li>
              ))}
            </ul>
            {error ? <p className="mt-2 text-sm text-primary">{error}</p> : null}
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-md px-3 py-2 text-sm text-muted hover:text-ink"
                onClick={() => {
                  setError(null)
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
