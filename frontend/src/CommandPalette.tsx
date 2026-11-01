import { useEffect, useMemo, useRef, useState } from 'react'

type Screen = 'dashboard' | 'library' | 'profile' | 'explorer' | 'questions'

type Command = {
  id: Screen | 'tour'
  title: string
  detail: string
  keywords: string
}

const commands: Command[] = [
  { id: 'dashboard', title: 'Overview', detail: 'Your workspace and applicability matches', keywords: 'home start dashboard' },
  { id: 'library', title: 'Regulations', detail: 'Search the official RBI corpus', keywords: 'documents browse search library' },
  { id: 'profile', title: 'Business profile', detail: 'Edit your regulated entity and attributes', keywords: 'organization account entity' },
  { id: 'explorer', title: 'Relationship explorer', detail: 'Trace amendments, replacements, and repeals', keywords: 'links history relations explorer' },
  { id: 'questions', title: 'Ask RAAY', detail: 'Get an answer with source evidence', keywords: 'question answer ask evidence' },
  { id: 'tour', title: 'Take the product tour', detail: 'Learn how the workspace is organized', keywords: 'help guide onboarding' },
]

type CommandPaletteProps = {
  open: boolean
  activeScreen: Screen
  onClose: () => void
  onNavigate: (screen: Screen) => void
  onStartTour: () => void
}

export default function CommandPalette({ open, activeScreen, onClose, onNavigate, onStartTour }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    return commands.filter((command) => !normalized || `${command.title} ${command.detail} ${command.keywords}`.toLowerCase().includes(normalized))
  }, [query])

  useEffect(() => {
    if (!open) return
    setQuery('')
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    inputRef.current?.focus()
    function manageKeyboard(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
        return
      }
      if (event.key !== 'Tab') return
      const dialog = inputRef.current?.closest<HTMLElement>('[role="dialog"]')
      const controls = dialog?.querySelectorAll<HTMLElement>('input:not([disabled]), button:not([disabled])')
      if (!controls?.length) return
      const first = controls[0]
      const last = controls[controls.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    window.addEventListener('keydown', manageKeyboard)
    return () => {
      window.removeEventListener('keydown', manageKeyboard)
      previousFocus?.focus()
    }
  }, [open, onClose])

  if (!open) return null

  function activate(command: Command) {
    if (command.id === 'tour') onStartTour()
    else onNavigate(command.id)
  }

  return <div className="command-backdrop" onMouseDown={(event) => {
    if (event.target === event.currentTarget) onClose()
  }}>
    <section className="command-dialog" role="dialog" aria-modal="true" aria-labelledby="command-title">
      <h2 id="command-title" className="sr-only">Jump to a workspace area</h2>
      <label className="command-search">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></svg>
        <input ref={inputRef} type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Where would you like to go?" aria-label="Search workspace actions" onKeyDown={(event) => {
          if (event.key === 'Enter' && results[0]) activate(results[0])
        }} />
        <button type="button" onClick={onClose} aria-label="Close quick navigation">Esc</button>
      </label>
      <p className="command-label">WORKSPACE</p>
      <div className="command-list" role="list">
        {results.map((command) => <button
          className={`command-item ${command.id === activeScreen ? 'current' : ''}`}
          type="button"
          role="listitem"
          key={command.id}
          onClick={() => activate(command)}
        >
          <span className="command-item-mark" aria-hidden="true">{command.id === activeScreen ? '•' : '↗'}</span>
          <span className="command-item-copy"><strong>{command.title}</strong><small>{command.detail}</small></span>
          {command.id === activeScreen && <span className="command-current">CURRENT</span>}
        </button>)}
        {results.length === 0 && <p className="command-empty">No workspace actions match “{query}”.</p>}
      </div>
      <footer className="command-footer"><span>Navigate without losing your place</span><span><kbd>Ctrl</kbd> or <kbd>⌘</kbd> + <kbd>K</kbd></span></footer>
    </section>
  </div>
}
