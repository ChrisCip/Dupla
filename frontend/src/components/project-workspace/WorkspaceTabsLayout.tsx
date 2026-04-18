import { useState, type ReactNode } from 'react'
import { PanelLeft } from 'lucide-react'

export type WorkspaceTabItem = { id: string; label: string }

type Props = {
  tabs: WorkspaceTabItem[]
  activeId: string
  onSelect: (id: string) => void
  labelledBy?: string
  children: ReactNode
}

export function WorkspaceTabsLayout({
  tabs,
  activeId,
  onSelect,
  labelledBy,
  children,
}: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const active = tabs.find((t) => t.id === activeId)

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden md:flex-row">
      <aside
        id="workspace-section-nav"
        aria-hidden={!sidebarOpen}
        className={`shrink-0 overflow-hidden border-black/10 bg-black/[0.02] transition-[width,max-height] duration-200 ease-out ${
          sidebarOpen
            ? 'max-h-[min(42vh,20rem)] w-full border-b md:max-h-none md:w-56 md:border-b-0 md:border-r'
            : 'max-h-0 w-full border-0 md:max-h-none md:w-0 md:border-0'
        }`}
      >
        <nav
          className="flex flex-col gap-1 overflow-y-auto p-2.5"
          role="tablist"
          aria-labelledby={labelledBy}
        >
          {tabs.map((t) => {
            const selected = t.id === activeId
            return (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={selected}
                id={`tab-${t.id}`}
                tabIndex={selected ? 0 : -1}
                className={`rounded-md px-3.5 py-2.5 text-left text-base font-medium outline-none transition-colors ${
                  selected
                    ? 'bg-primary/10 text-ink shadow-sm'
                    : 'text-muted hover:bg-black/[0.04] hover:text-ink'
                } focus-visible:ring-2 focus-visible:ring-primary/35 focus-visible:ring-offset-2`}
                onClick={() => {
                  onSelect(t.id)
                  if (typeof window !== 'undefined' && window.matchMedia('(max-width: 767px)').matches) {
                    setSidebarOpen(false)
                  }
                }}
              >
                {t.label}
              </button>
            )
          })}
        </nav>
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-black/10 bg-white px-3 py-2.5 sm:px-4">
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-md border border-black/12 bg-white px-3 py-2 text-base font-medium text-ink shadow-sm outline-none transition hover:bg-black/[0.03] focus-visible:ring-2 focus-visible:ring-primary/35 focus-visible:ring-offset-2"
            aria-expanded={sidebarOpen}
            aria-controls="workspace-section-nav"
            onClick={() => setSidebarOpen((o) => !o)}
          >
            <PanelLeft
              className={`h-4 w-4 shrink-0 text-muted transition-transform ${sidebarOpen ? 'text-primary' : ''}`}
              aria-hidden
            />
            Secciones
          </button>
          {active ? (
            <h2 className="min-w-0 flex-1 text-lg font-semibold tracking-tight text-ink sm:text-xl">
              {active.label}
            </h2>
          ) : null}
        </div>
        <div
          role="tabpanel"
          aria-labelledby={active ? `tab-${active.id}` : undefined}
          className="flex min-h-0 flex-1 flex-col overflow-y-auto px-3 py-4 sm:px-5 sm:py-5"
        >
          {children}
        </div>
      </div>
    </div>
  )
}
