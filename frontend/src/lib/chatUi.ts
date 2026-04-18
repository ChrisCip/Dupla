import type { ChatConversationKind, ChatMessage } from '../types/chat'

const GROUP_MS = 5 * 60 * 1000

export type MessageDisplayGroup = {
  key: string
  author: { uuid: string; email: string }
  messages: ChatMessage[]
}

export function chatKindLabel(kind: ChatConversationKind): string {
  switch (kind) {
    case 'GENERAL':
      return 'Avisos'
    case 'DIRECT':
      return 'Directo'
    case 'GROUP':
      return 'Grupo'
    case 'PROJECT':
      return 'Proyecto'
    default:
      return ''
  }
}

export function formatRelativeChatTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const diff = Date.now() - d.getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 45) return 'ahora'
  const min = Math.floor(sec / 60)
  if (min < 60) return `hace ${min} min`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `hace ${hr} h`
  const days = Math.floor(hr / 24)
  if (days < 7) return `hace ${days} d`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function formatMessageTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

export function groupMessagesForDisplay(messages: ChatMessage[]): MessageDisplayGroup[] {
  const sorted = [...messages].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  )
  const groups: MessageDisplayGroup[] = []
  for (const m of sorted) {
    const last = groups[groups.length - 1]
    const prevMsg = last?.messages[last.messages.length - 1]
    const sameAuthor = Boolean(prevMsg && prevMsg.author.uuid === m.author.uuid)
    const closeInTime =
      prevMsg &&
      Math.abs(new Date(m.created_at).getTime() - new Date(prevMsg.created_at).getTime()) <= GROUP_MS
    if (last && sameAuthor && closeInTime) {
      last.messages.push(m)
    } else {
      groups.push({ key: m.uuid, author: m.author, messages: [m] })
    }
  }
  return groups
}

export function isOptimisticMessageId(uuid: string): boolean {
  return uuid.startsWith('optimistic-')
}
