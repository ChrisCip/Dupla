export type ChatConversationKind = 'GENERAL' | 'DIRECT' | 'GROUP'

export type ChatConversationSummary = {
  uuid: string
  kind: ChatConversationKind
  display_title: string
  last_message_at: string | null
}

export type ChatMessage = {
  uuid: string
  conversation_uuid: string
  body: string
  created_at: string
  author: { uuid: string; email: string }
}

export type ChatDirectoryUser = {
  uuid: string
  email: string
}
