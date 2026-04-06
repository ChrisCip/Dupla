import { useEffect, useRef, useState } from 'react'

import { apiFetch } from '../api/client'
import { Card } from '../components/Card'
import { PrimaryButton } from '../components/PrimaryButton'
import { useAuthStore } from '../store/authStore'
import { useChatStore } from '../store/chatStore'
import type { ChatMessage } from '../types/chat'

export function ChatPage() {
  const token = useAuthStore((s) => s.token)
  const userUuid = useAuthStore((s) => s.userUuid)
  const messages = useChatStore((s) => s.messages)
  const appendMessages = useChatStore((s) => s.appendMessages)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  async function send(e: React.FormEvent) {
    e.preventDefault()
    const text = draft.trim()
    if (!token || !text) return
    setError(null)
    setSending(true)
    try {
      const res = await apiFetch('/api/chat/messages', {
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
    } finally {
      setSending(false)
    }
  }

  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-ink">Chat interno</h1>
        <p className="mt-2 text-sm text-muted">
          Mensajes del equipo. Recibirás un indicador en el menú si hay mensajes nuevos mientras navegas otras
          secciones.
        </p>
      </div>

      <Card className="flex max-h-[min(70vh,560px)] flex-col overflow-hidden p-0">
        <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
          {messages.length === 0 ? (
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
            disabled={sending}
            maxLength={4000}
          />
          <div className="mt-2 flex justify-end">
            <PrimaryButton type="submit" disabled={sending || !draft.trim()}>
              {sending ? 'Enviando…' : 'Enviar'}
            </PrimaryButton>
          </div>
        </form>
      </Card>
    </>
  )
}
