import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { useAuthStore } from '../store/authStore'
import { useChatStore } from '../store/chatStore'
import type { ChatMessage } from '../types/chat'

export function useChatSync() {
  const token = useAuthStore((s) => s.token)
  const location = useLocation()
  const setMessages = useChatStore((s) => s.setMessages)
  const clearUnread = useChatStore((s) => s.clearUnread)
  const reset = useChatStore((s) => s.reset)

  const isChatPath = location.pathname === '/app/chat'

  useEffect(() => {
    if (!token) reset()
  }, [token, reset])

  useEffect(() => {
    if (isChatPath) clearUnread()
  }, [isChatPath, clearUnread])

  useEffect(() => {
    if (!token) return
    let cancelled = false
    async function boot() {
      const res = await apiFetch('/api/chat/messages', { token })
      if (!res.ok || cancelled) return
      const data = (await res.json()) as ChatMessage[]
      setMessages(data)
    }
    void boot()
    return () => {
      cancelled = true
    }
  }, [token, setMessages])

  const chatPathRef = useRef(isChatPath)
  useEffect(() => {
    chatPathRef.current = isChatPath
  }, [isChatPath])

  useEffect(() => {
    if (!token) return
    const id = window.setInterval(async () => {
      const { messages } = useChatStore.getState()
      const last = messages[messages.length - 1]
      const url = last
        ? `/api/chat/messages?after_uuid=${encodeURIComponent(last.uuid)}`
        : '/api/chat/messages'
      const res = await apiFetch(url, { token })
      if (!res.ok) return
      const batch = (await res.json()) as ChatMessage[]
      if (batch.length === 0) return
      const me = useAuthStore.getState().userUuid
      const onChat = chatPathRef.current
      if (!onChat && me && batch.some((m) => m.author.uuid !== me)) {
        useChatStore.getState().setUnread(true)
      }
      useChatStore.getState().appendMessages(batch)
    }, 4000)
    return () => window.clearInterval(id)
  }, [token])
}
