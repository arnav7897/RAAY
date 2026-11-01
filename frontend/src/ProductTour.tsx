import { useEffect, useRef } from 'react'

export type TourStep = {
  section: string
  title: string
  description: string
  detail: string
}

type ProductTourProps = {
  step: number
  steps: TourStep[]
  onContinue: () => void
  onSkip: () => void
}

export default function ProductTour({ step, steps, onContinue, onSkip }: ProductTourProps) {
  const current = steps[step]
  const dialogRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    const firstButton = dialog?.querySelector<HTMLButtonElement>('button:not([disabled])')
    firstButton?.focus()

    function manageKeyboard(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onSkip()
        return
      }
      if (event.key !== 'Tab' || !dialog) return
      const buttons = Array.from(dialog.querySelectorAll<HTMLButtonElement>('button:not([disabled])'))
      const first = buttons[0]
      const last = buttons[buttons.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first?.focus()
      }
    }
    window.addEventListener('keydown', manageKeyboard)
    return () => window.removeEventListener('keydown', manageKeyboard)
  }, [onSkip])

  if (!current) return null

  return (
    <div className="tour-backdrop" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onSkip()
    }}>
      <section ref={dialogRef} className="tour-dialog" role="dialog" aria-modal="true" aria-labelledby="tour-title">
        <div className="tour-topline">
          <span className="tour-brand"><span className="brand-mark">R</span> RAAY GUIDE</span>
          <button className="icon-button tour-close" type="button" onClick={onSkip} aria-label="Close product tour">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
          </button>
        </div>
        <div className="tour-progress" aria-label={`Step ${step + 1} of ${steps.length}`}>
          {steps.map((item, index) => <span key={item.section} className={index <= step ? 'complete' : ''} />)}
        </div>
        <p className="eyebrow">{String(step + 1).padStart(2, '0')} / {String(steps.length).padStart(2, '0')} · {current.section}</p>
        <h2 id="tour-title">{current.title}</h2>
        <p className="tour-description">{current.description}</p>
        <div className="tour-detail"><span className="tour-detail-mark" aria-hidden="true">✓</span><p>{current.detail}</p></div>
        <div className="tour-footer">
          <button className="text-button" type="button" onClick={onSkip}>Finish later</button>
          <button className="primary-button" type="button" onClick={onContinue}>
            {step === steps.length - 1 ? 'Explore RAAY' : 'Next'}
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6" /></svg>
          </button>
        </div>
      </section>
    </div>
  )
}
