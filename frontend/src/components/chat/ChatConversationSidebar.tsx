import { Card } from '../Card'
import { PrimaryButton } from '../PrimaryButton'
import { chatKindLabel, formatRelativeChatTime } from '../../lib/chatUi'
import type { ChatConversationSummary } from '../../types/chat'

type ChatConversationSidebarProps = {
  conversations: ChatConversationSummary[]
  activeConversationUuid: string | null
  onSelect: (uuid: string) => void
  onNewChat: () => void
  onNewGroup: () => void
}

export function ChatConversationSidebar({
  conversations,
  activeConversationUuid,
  onSelect,
  onNewChat,
  onNewGroup,
}: ChatConversationSidebarProps) {
  return (
    <aside className="w-full shrink-0 lg:w-80">
      <Card className="flex flex-col gap-4 p-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <PrimaryButton type="button" className="w-full sm:flex-1" onClick={onNewChat}>
            Nuevo chat
          </PrimaryButton>
          <button
            type="button"
            className="w-full rounded-md border border-black/15 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-wide text-ink shadow-sm hover:border-primary/30 sm:w-auto sm:shrink-0"
            onClick={onNewGroup}
          >
            Nuevo grupo
          </button>
        </div>
        <div>
          <div className="du-label">Conversaciones</div>
          <ul className="mt-2 max-h-[min(60vh,520px)] space-y-1 overflow-y-auto pr-0.5">
            {conversations.map((c) => {
              const active = c.uuid === activeConversationUuid
              const unread = (c.unread_count ?? 0) > 0
              const preview = c.last_message_preview?.trim() || 'Sin mensajes aún'
              const when = formatRelativeChatTime(c.last_message_at)
              return (
                <li key={c.uuid}>
                  <button
                    type="button"
                    onClick={() => onSelect(c.uuid)}
                    className={`w-full rounded-lg border px-3 py-2.5 text-left text-sm transition ${
                      active
                        ? 'border-primary/40 bg-primary/5 text-ink shadow-sm'
                        : 'border-black/10 bg-white hover:border-primary/25'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="min-w-0 flex-1 font-medium leading-snug">{c.display_title}</span>
                      {unread ? (
                        <span
                          className="mt-0.5 inline-flex min-h-5 min-w-5 shrink-0 items-center justify-center rounded-full bg-primary px-1.5 text-[10px] font-bold leading-none text-white"
                          aria-label={`${c.unread_count} sin leer`}
                        >
                          {c.unread_count! > 99 ? '99+' : c.unread_count}
                        </span>
                      ) : null}
                    </div>
                    <div className="du-meta mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                      <span>{chatKindLabel(c.kind)}</span>
                      {c.participant_count != null && c.kind !== 'DIRECT' ? (
                        <span>· {c.participant_count} en el chat</span>
                      ) : null}
                      {when ? <span>· {when}</span> : null}
                    </div>
                    <p
                      className={`mt-1 line-clamp-2 text-xs leading-snug ${
                        unread ? 'font-medium text-ink' : 'text-muted'
                      }`}
                    >
                      {preview}
                    </p>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      </Card>
    </aside>
  )
}
