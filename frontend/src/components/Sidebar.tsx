import { NavLink } from 'react-router-dom'

import { DuplaLogo } from './DuplaLogo'
import { useAuthStore } from '../store/authStore'
import { useChatStore } from '../store/chatStore'

const linkClass =
  'flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium text-ink outline-none transition-colors duration-150 hover:bg-black/5 active:bg-black/10 focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 focus-visible:ring-offset-white'
const activeClass = 'bg-primary/10 text-primary'

export function Sidebar() {
  const role = useAuthStore((s) => s.role)
  const hasUnread = useChatStore((s) => s.hasUnread)

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-black/10 bg-white">
      <div className="border-b border-black/10 px-4 py-6">
        <DuplaLogo className="h-14 w-auto max-w-[min(100%,320px)] object-contain object-left" />
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 p-3" aria-label="Principal">
        <NavLink
          to="/app/projects"
          className={({ isActive }) => `${linkClass} ${isActive ? activeClass : ''}`}
          end
        >
          Proyectos
        </NavLink>
        <NavLink
          to="/app/chat"
          className={({ isActive }) => `${linkClass} ${isActive ? activeClass : ''}`}
        >
          <span>Chat interno</span>
          {hasUnread ? (
            <span
              className="h-2 w-2 shrink-0 rounded-full bg-primary"
              aria-label="Mensajes nuevos"
            />
          ) : null}
        </NavLink>
        <NavLink
          to="/app/tasks"
          className={({ isActive }) => `${linkClass} ${isActive ? activeClass : ''}`}
        >
          Tablero
        </NavLink>
        {role === 'MASTER' ? (
          <NavLink
            to="/app/admin"
            className={({ isActive }) => `${linkClass} ${isActive ? activeClass : ''}`}
          >
            Administración
          </NavLink>
        ) : null}
      </nav>
    </aside>
  )
}
