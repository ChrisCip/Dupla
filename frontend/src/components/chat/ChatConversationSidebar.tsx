import { Card } from '../Card'
import { PrimaryButton } from '../PrimaryButton'
import {
  chatKindLabel,
  formatGroupParticipantEmails,
  formatRelativeChatTime,
} from '../../lib/chatUi'
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
    <aside className="flex h-full min-h-0 w-full shrink-0 flex-col lg:w-80">
      <Card className="flex h-full min-h-0 flex-col gap-4 overflow-hidden border-0 bg-transparent p-4 shadow-none">
        <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:items-center">
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
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="du-label">Conversaciones</div>
          <ul className="mt-2 min-h-0 flex-1 space-y-1 overflow-y-auto pr-0.5">
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
                      {c.participant_count != null && c.kind !== 'DIRECT' && c.kind !== 'GROUP' ? (
                        <span>· {c.participant_count} en el chat</span>
                      ) : null}
                      {when ? <span>· {when}</span> : null}
                    </div>
                    {c.kind === 'GROUP' && formatGroupParticipantEmails(c.participants) ? (
                      <p className="mt-1 line-clamp-3 text-[11px] leading-snug text-muted">
                        {formatGroupParticipantEmails(c.participants)}
                      </p>
                    ) : c.kind === 'GROUP' && c.participant_count != null ? (
                      <p className="mt-1 text-[11px] text-muted">{c.participant_count} personas</p>
                    ) : null}
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
