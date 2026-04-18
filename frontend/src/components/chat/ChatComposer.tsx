import { type FormEvent, useEffect, useRef } from 'react'

import { PrimaryButton } from '../PrimaryButton'

type ChatComposerProps = {
  value: string
  onChange: (value: string) => void
  onSend: () => void | Promise<void>
  disabled?: boolean
  sending?: boolean
  error?: string | null
}

export function ChatComposer({
  value,
  onChange,
  onSend,
  disabled,
  sending,
  error,
}: ChatComposerProps) {
  const taRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = taRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }, [value])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    void onSend()
  }

  return (
    <form
      className="border-t border-black/10 bg-black/2 px-4 py-3"
      onSubmit={handleSubmit}
    >
      {error ? <p className="mb-2 text-sm text-primary">{error}</p> : null}
      <label className="du-label sr-only" htmlFor="chat-composer-input">
        Mensaje
      </label>
      <div className="flex items-end gap-2">
        <textarea
          id="chat-composer-input"
          ref={taRef}
          rows={1}
          className="du-input max-h-[120px] min-h-[44px] flex-1 resize-none py-2.5"
          placeholder="Escribe un mensaje… (Enter envía, Shift+Enter nueva línea)"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={sending || disabled}
          maxLength={4000}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void onSend()
            }
          }}
        />
        <PrimaryButton
          type="submit"
          className="shrink-0"
          disabled={sending || !value.trim() || disabled}
        >
          {sending ? 'Enviando…' : 'Enviar'}
        </PrimaryButton>
      </div>
    </form>
  )
}
