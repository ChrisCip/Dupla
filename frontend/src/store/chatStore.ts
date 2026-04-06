import { create } from 'zustand'

import type { ChatMessage } from '../types/chat'

type ChatState = {
  messages: ChatMessage[]
  hasUnread: boolean
  setMessages: (messages: ChatMessage[]) => void
  appendMessages: (incoming: ChatMessage[]) => void
  setUnread: (value: boolean) => void
  clearUnread: () => void
  reset: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  hasUnread: false,
  setMessages: (messages) => set({ messages }),
  appendMessages: (incoming) => {
    if (incoming.length === 0) return
    const seen = new Set(get().messages.map((m) => m.uuid))
    const next = [...get().messages]
    for (const m of incoming) {
      if (!seen.has(m.uuid)) {
        seen.add(m.uuid)
        next.push(m)
      }
    }
    set({ messages: next })
  },
  setUnread: (value) => set({ hasUnread: value }),
  clearUnread: () => set({ hasUnread: false }),
  reset: () => set({ messages: [], hasUnread: false }),
}))
