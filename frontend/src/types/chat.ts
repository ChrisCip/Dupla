export type ChatMessage = {
  uuid: string
  body: string
  created_at: string
  author: { uuid: string; email: string }
}
