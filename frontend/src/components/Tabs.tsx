import type { ReactNode } from 'react'

export type TabItem = { id: string; label: string }

type Props = {
  tabs: TabItem[]
  value: string
  onChange: (id: string) => void
  children: ReactNode
  labelledBy?: string
}

export function Tabs({ tabs, value, onChange, children, labelledBy }: Props) {
  return (
    <div>
      <div
        className="flex flex-wrap gap-1 border-b border-black/10"
        role="tablist"
        aria-labelledby={labelledBy}
      >
        {tabs.map((t) => {
          const selected = t.id === value
          return (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={selected}
              id={`tab-${t.id}`}
              tabIndex={selected ? 0 : -1}
              className={`relative -mb-px border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                selected
                  ? 'border-primary text-ink'
                  : 'border-transparent text-muted hover:text-ink'
              }`}
              onClick={() => onChange(t.id)}
            >
              {t.label}
            </button>
          )
        })}
      </div>
      <div
        role="tabpanel"
        aria-labelledby={`tab-${value}`}
        className="pt-8"
      >
        {children}
      </div>
    </div>
  )
}
