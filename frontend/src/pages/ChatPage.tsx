import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { Card } from '../components/Card'
import { ChatComposer } from '../components/chat/ChatComposer'
import { ChatConversationSidebar } from '../components/chat/ChatConversationSidebar'
import { ChatDirectModal } from '../components/chat/ChatDirectModal'
import { ChatGroupModal } from '../components/chat/ChatGroupModal'
import { ChatMessageList } from '../components/chat/ChatMessageList'
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
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-4 shrink-0 md:mb-6">
        <h1 className="text-xl font-semibold text-ink md:text-2xl">Chat interno</h1>
        <p className="mt-2 text-sm text-muted">
          Canal general para avisos del equipo, chats uno a uno y grupos. El menú avisa si hay actividad nueva
          mientras navegas otras secciones.
        </p>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-4 lg:flex-row lg:items-stretch">
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

        <Card className="flex min-h-[min(40dvh,320px)] min-w-0 flex-1 flex-col overflow-hidden p-0 lg:min-h-0">
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

      <ChatDirectModal
        open={showDm}
        dmTarget={dmTarget}
        setDmTarget={setDmTarget}
        directory={directory}
        error={error}
        onBackdropClose={() => {
          setError(null)
          setShowDm(false)
        }}
        onCancel={() => {
          setError(null)
          setShowDm(false)
        }}
        onSubmit={openDirect}
      />

      <ChatGroupModal
        open={showGroup}
        groupTitle={groupTitle}
        setGroupTitle={setGroupTitle}
        groupMemberSearch={groupMemberSearch}
        setGroupMemberSearch={setGroupMemberSearch}
        groupSelectedUuids={groupSelectedUuids}
        directory={directory}
        groupPickerCandidates={groupPickerCandidates}
        error={error}
        onBackdropClose={() => {
          setError(null)
          setGroupTitle('')
          setGroupMemberSearch('')
          setGroupSelectedUuids([])
          setShowGroup(false)
        }}
        onCancel={() => {
          setError(null)
          setGroupTitle('')
          setGroupMemberSearch('')
          setGroupSelectedUuids([])
          setShowGroup(false)
        }}
        onAddMember={addGroupMember}
        onRemoveMember={removeGroupMember}
        onCreateGroup={createGroup}
      />
    </div>
  )
}
