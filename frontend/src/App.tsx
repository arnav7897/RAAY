import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { Answer, Document, Profile, Relationship, RelevantDocument } from './types'
import ProductTour from './ProductTour'
import type { TourStep } from './ProductTour'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
type Screen = 'dashboard' | 'library' | 'profile' | 'explorer' | 'questions'
type Account = { id: number; email: string }

const tourSteps: TourStep[] = [
  {
    section: 'OVERVIEW',
    title: 'Start with what applies to you.',
    description: 'Your workspace brings official RBI documents and profile matches into one clear view.',
    detail: 'Set up your organization profile to see evidence-backed applicability matches here.',
  },
  {
    section: 'REGULATIONS',
    title: 'Browse the corpus on its own page.',
    description: 'Search official RBI documents and filter them by current lifecycle status.',
    detail: 'This is a curated corpus, not a complete search of every RBI publication.',
  },
  {
    section: 'YOUR PROFILE',
    title: 'Tell RAAY what kind of organization you are.',
    description: 'Choose your regulated entity and add only the business facts you know.',
    detail: 'RAAY uses these details to assess applicability. Your profile stays private to your account.',
  },
  {
    section: 'RELATIONSHIP EXPLORER',
    title: 'Follow each rule back to its source.',
    description: 'Explore verified amendments, replacements, repeals, and the evidence behind each link.',
    detail: 'Only quote-backed, verified relationships appear as legal links.',
  },
  {
    section: 'ASK RAAY',
    title: 'Ask a question. Check every citation.',
    description: 'Choose an RBI document and ask about its requirements in plain language.',
    detail: 'Every supported claim includes a source quote and location. Unsupported claims are rejected.',
  },
]

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [dataLoaded, setDataLoaded] = useState(false)
  const [user, setUser] = useState<Account | null>(null)
  const [screen, setScreen] = useState<Screen>('dashboard')
  const [documents, setDocuments] = useState<Document[]>([])
  const [relevant, setRelevant] = useState<RelevantDocument[]>([])
  const [profile, setProfile] = useState<Profile>({ entity_code: 'NBFC_MFI', attributes: {} })
  const [hasProfile, setHasProfile] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [relationships, setRelationships] = useState<Relationship[]>([])
  const [relationshipsLoading, setRelationshipsLoading] = useState(false)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [tourStep, setTourStep] = useState<number | null>(null)
  const [questionStartedAt, setQuestionStartedAt] = useState<number | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  const api = useCallback(async <T,>(path: string, init: RequestInit = {}): Promise<T> => {
    const response = await fetch(`${API}${path}`, {
      ...init,
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...init.headers },
    })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      throw new Error(body.detail || `Request failed (${response.status})`)
    }
    if (response.status === 204) return undefined as T
    return response.json() as Promise<T>
  }, [])

  const dismissTour = useCallback(() => {
    if (user) window.localStorage.setItem(`raay-tour-v1:${user.id}`, 'complete')
    setTourStep(null)
  }, [user])

  const load = useCallback(async () => {
    setBusy(true)
    setError('')
    try {
      const [docs, savedProfile] = await Promise.all([
        api<Document[]>('/documents'),
        api<Profile | null>('/profile'),
      ])
      setDocuments(docs)
      setSelectedId((current) => current ?? docs[0]?.id ?? null)
      if (savedProfile) {
        setProfile(savedProfile)
        setHasProfile(true)
        const result = await api<{ documents: RelevantDocument[] }>('/relevant')
        setRelevant(result.documents)
      } else {
        setHasProfile(false)
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load RAAY data')
    } finally {
      setBusy(false)
      setDataLoaded(true)
    }
  }, [api])

  useEffect(() => {
    void fetch(`${API}/auth/me`, { credentials: 'include' })
      .then(async (response) => response.ok ? response.json() as Promise<Account> : null)
      .then((account) => {
        if (account) {
          setUser(account)
          setIsAuthenticated(true)
        }
      })
      .catch(() => null)
      .finally(() => setIsLoading(false))
  }, [])

  useEffect(() => { if (isAuthenticated) void load() }, [isAuthenticated, load])

  useEffect(() => {
    if (!isAuthenticated || !dataLoaded || !user) return
    const key = `raay-tour-v1:${user.id}`
    if (window.localStorage.getItem(key) !== 'complete') setTourStep(0)
  }, [dataLoaded, isAuthenticated, user])

  useEffect(() => {
    if (questionStartedAt === null) return
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - questionStartedAt) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [questionStartedAt])

  useEffect(() => {
    if (!selectedId || !isAuthenticated) return
    let active = true
    setRelationshipsLoading(true)
    void api<Relationship[]>(`/documents/${selectedId}/relations`)
      .then((items) => { if (active) setRelationships(items) })
      .catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : 'Could not load relationships') })
      .finally(() => { if (active) setRelationshipsLoading(false) })
    return () => { active = false }
  }, [api, isAuthenticated, selectedId])

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const saved = await api<Profile>('/profile', { method: 'PUT', body: JSON.stringify(profile) })
      setProfile(saved)
      setHasProfile(true)
      const result = await api<{ documents: RelevantDocument[] }>('/relevant')
      setRelevant(result.documents)
      setScreen('dashboard')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save profile')
    } finally { setBusy(false) }
  }

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedId) return
    setBusy(true)
    setError('')
    setAnswer(null)
    setElapsedSeconds(0)
    setQuestionStartedAt(Date.now())
    try {
      const response = await api<Answer>('/questions', {
        method: 'POST', body: JSON.stringify({ question, document_ids: [selectedId] }),
      })
      setAnswer(response)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Question failed')
    } finally {
      setBusy(false)
      setQuestionStartedAt(null)
    }
  }

  if (isLoading) return <div className="loading">Loading RAAY…</div>
  if (!isAuthenticated) return <Login onAuthenticated={(account) => { setUser(account); setIsAuthenticated(true) }} />

  async function signOut() {
    try { await api('/auth/logout', { method: 'POST' }) } finally {
      setUser(null)
      setIsAuthenticated(false)
      setDocuments([])
      setRelevant([])
      setHasProfile(false)
      setScreen('dashboard')
    }
  }

  function continueTour() {
    if (tourStep === null) return
    if (tourStep === tourSteps.length - 1) {
      dismissTour()
      return
    }
    const nextStep = tourStep + 1
    setScreen(['dashboard', 'library', 'profile', 'explorer', 'questions'][nextStep] as Screen)
    setTourStep(nextStep)
  }

  function startTour() {
    setScreen('dashboard')
    setTourStep(0)
  }

  const selected = documents.find((document) => document.id === selectedId)
  const nav: { id: Screen; label: string; icon: string }[] = [
    { id: 'dashboard', label: 'Overview', icon: 'overview' },
    { id: 'library', label: 'Regulations', icon: 'library' },
    { id: 'profile', label: 'My profile', icon: 'profile' },
    { id: 'explorer', label: 'Relationship explorer', icon: 'explorer' },
    { id: 'questions', label: 'Ask RAAY', icon: 'questions' },
  ]

  return <div className="shell">
    <aside className="sidebar">
      <a className="brand" href="#overview" onClick={() => setScreen('dashboard')}><span className="brand-mark">R</span><span>raay<span className="brand-dot">.</span></span></a>
      <div className="workspace-label">WORKSPACE</div>
      <nav aria-label="Main navigation">{nav.map((item) => <button key={item.id} type="button" className={`nav-item ${screen === item.id ? 'active' : ''}`} aria-current={screen === item.id ? 'page' : undefined} onClick={() => setScreen(item.id)}><Icon name={item.icon} /><span>{item.label}</span><svg className="nav-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg></button>)}</nav>
      <div className="sidebar-bottom"><div className="source-live"><i /> Official RBI corpus<br /><small>Evidence stays linked to source</small></div><button className="signout" onClick={() => void signOut()}>Sign out <span aria-hidden="true">↗</span></button></div>
    </aside>

    <main className="main">
      <header className="topbar"><div className="breadcrumb"><span className="breadcrumb-mark">RAAY</span><span className="breadcrumb-separator">/</span> {nav.find((item) => item.id === screen)?.label}</div><div className="topbar-actions"><button className="tour-launch" type="button" onClick={startTour}><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.6 9a2.5 2.5 0 1 1 4.4 1.6c-1.2 1.1-2 1.4-2 3"/><path d="M12 17.5v.1"/></svg><span>Take a tour</span></button><div className="user-chip"><span className="user-avatar">{(user?.email || 'U').slice(0, 1).toUpperCase()}</span><span>{user?.email || 'Account'}</span></div><button className="mobile-signout" type="button" onClick={() => void signOut()} aria-label="Sign out"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 17l5-5-5-5M15 12H3"/><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6"/></svg></button></div></header>
      <div className="content">
        {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError('')}>Dismiss</button></div>}
        {screen === 'dashboard' && <Dashboard documents={documents} relevant={relevant} hasProfile={hasProfile} busy={busy} onProfile={() => setScreen('profile')} onSelect={(id) => { setSelectedId(id); setScreen('explorer') }} onAsk={() => setScreen('questions')} />}
        {screen === 'library' && <DocumentLibrary documents={documents} busy={busy} onSelect={(id) => { setSelectedId(id); setScreen('explorer') }} />}
        {screen === 'profile' && <ProfileScreen profile={profile} setProfile={setProfile} onSave={saveProfile} busy={busy} />}
        {screen === 'explorer' && <Explorer documents={documents} selectedId={selectedId} setSelectedId={setSelectedId} selected={selected} relations={relationships} loading={relationshipsLoading} />}
        {screen === 'questions' && <QuestionScreen documents={documents} selectedId={selectedId} setSelectedId={setSelectedId} question={question} setQuestion={setQuestion} onAsk={ask} answer={answer} busy={busy} elapsedSeconds={elapsedSeconds} />}
      </div>
    </main>
    {tourStep !== null && <ProductTour step={tourStep} steps={tourSteps} onContinue={continueTour} onSkip={dismissTour} />}
  </div>
}

function Icon({ name }: { name: string }) {
  const icon = name === 'overview' ? <><rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/></>
    : name === 'library' ? <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 1 4 17.5z"/><path d="M4 6h13M8 9h8M8 12h8M8 15h6"/></>
    : name === 'profile' ? <><circle cx="12" cy="8" r="3.5"/><path d="M4.5 20c.8-3.3 3.4-5 7.5-5s6.7 1.7 7.5 5"/></>
      : name === 'explorer' ? <><circle cx="7" cy="7" r="3"/><circle cx="17" cy="17" r="3"/><path d="M9.2 9.2 14.8 14.8M17 4v5M14.5 6.5h5M7 15v5M4.5 17.5h5"/></>
        : <><path d="M20 11.5a7.5 7.5 0 0 1-7.5 7.5H5l1.5-3A7.5 7.5 0 1 1 20 11.5Z"/><path d="M8.5 11.5h7M8.5 14.5h4"/></>
  return <svg className="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icon}</svg>
}

function Login({ onAuthenticated }: { onAuthenticated: (account: Account) => void }) {
  const [registering, setRegistering] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const response = await fetch(`${API}/auth/${registering ? 'register' : 'login'}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`)
      onAuthenticated(body as Account)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not sign in')
    } finally { setBusy(false) }
  }

  return <main className="login-page">
    <div className="login-layout">
      <section className="login-story">
        <a className="brand login-brand" href="#home"><span className="brand-mark">R</span><span>raay<span className="brand-dot">.</span></span></a>
        <p className="eyebrow">REGULATORY INTELLIGENCE, GROUNDED</p>
        <h1>Know what applies.<br /><em>See the evidence.</em></h1>
        <p className="login-copy">A calmer way to understand RBI rules. Follow every answer to the official source behind it.</p>
        <div className="login-proof"><div><span className="proof-icon"><Icon name="explorer" /></span><span><b>Verified relationships</b><small>Trace changes back to source text.</small></span></div><div><span className="proof-icon"><Icon name="questions" /></span><span><b>Cited answers</b><small>Check the quote and its location.</small></span></div><div><span className="proof-icon"><Icon name="overview" /></span><span><b>Your organization</b><small>See only evidence-backed matches.</small></span></div></div>
        <p className="login-side-note">BUILT ON OFFICIAL RBI SOURCES <span>·</span> EVIDENCE FIRST</p>
      </section>
      <section className="login-card">
        <p className="eyebrow">{registering ? 'CREATE YOUR WORKSPACE' : 'WELCOME BACK'}</p>
        <h2>{registering ? 'Create your account' : 'Sign in to RAAY'}</h2>
        <p className="login-form-copy">{registering ? 'Your regulatory workspace starts with a private account.' : 'Your saved profile and evidence are waiting for you.'}</p>
        <form className="auth-form" onSubmit={submit}>
          <label>Email address<input className="auth-input" type="email" autoComplete="email" maxLength={254} required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@organization.com" /></label>
          <label>Password<span className="password-wrap"><input className="auth-input" type={showPassword ? 'text' : 'password'} autoComplete={registering ? 'new-password' : 'current-password'} minLength={registering ? 15 : 1} maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} placeholder={registering ? 'At least 15 characters' : 'Enter your password'} /><button type="button" className="password-toggle" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? 'Hide' : 'Show'}</button></span></label>
          {registering && <p className="password-hint">Use at least 15 characters. A password manager is welcome.</p>}
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="primary-button login-button" disabled={busy}>{busy ? 'Please wait…' : registering ? 'Create account' : 'Sign in'} <span aria-hidden="true">→</span></button>
        </form>
        <div className="login-switch">{registering ? 'Already have an account?' : 'New to RAAY?'} <button type="button" onClick={() => { setRegistering(!registering); setError('') }}>{registering ? 'Sign in' : 'Create an account'}</button></div>
        <p className="privacy-note"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg> Passwords are protected with a salted password hash.</p>
      </section>
    </div>
  </main>
}

function Dashboard({ documents, relevant, hasProfile, busy, onProfile, onSelect, onAsk }: { documents: Document[]; relevant: RelevantDocument[]; hasProfile: boolean; busy: boolean; onProfile: () => void; onSelect: (id: number) => void; onAsk: () => void }) {
  return <div className="dashboard-page">
    <div className="page-heading"><div><p className="eyebrow">YOUR REGULATORY WORKSPACE</p><h1>Your RBI desk<span className="heading-dot">.</span></h1><p className="subheading">A clear starting point for the rules that may apply to your organization.</p></div><span className="corpus-status"><i /> {documents.length} indexed documents</span></div>
    <section className="overview-welcome"><div><p className="eyebrow">OFFICIAL SOURCES, TRACEABLE ANSWERS</p><h2>{hasProfile ? 'Your workspace is ready.' : 'Start with your organization.'}</h2><p>{hasProfile ? 'Ask a question or review the evidence connected to your profile.' : 'Add your entity type to see supported applicability matches. You can browse documents at any time.'}</p></div><button className="primary-button" type="button" onClick={hasProfile ? onAsk : onProfile}>{hasProfile ? 'Ask a question' : 'Set up profile'} <span>→</span></button></section>
    <section className="section-block"><div className="section-heading"><div><p className="eyebrow">PERSONALIZED FOR YOU</p><h2>Relevant to your organization</h2></div><button className="text-button" type="button" onClick={onProfile}>{hasProfile ? 'Edit profile' : 'Create profile'}<span aria-hidden="true"> ↗</span></button></div>
      {!hasProfile ? <div className="empty-card"><div><h3>Profile not set up yet</h3><p>RAAY will show a match only when stored RBI evidence supports it.</p></div><button className="secondary-button" type="button" onClick={onProfile}>Set up profile <span>→</span></button></div> : busy ? <div className="loading-card"><span className="spinner"/><span>Checking evidence against your profile…</span></div> : relevant.length ? <div className="document-grid">{relevant.slice(0, 2).map((doc) => <DocumentCard key={doc.id} doc={doc} onClick={() => onSelect(doc.id)} />)}</div> : <div className="empty-card"><div><h3>No supported matches yet</h3><p>Current stored applicability evidence did not produce a match. Browse the corpus to inspect source material.</p></div></div>}
    </section>
    <section className="overview-links" aria-label="Continue"><button type="button" onClick={() => documents[0] && onSelect(documents[0].id)}><span className="overview-link-number">01</span><span><b>Follow a document</b><small>See verified amendments, replacements, and repeals.</small></span><span aria-hidden="true">→</span></button><button type="button" onClick={onAsk}><span className="overview-link-number">02</span><span><b>Ask about an RBI rule</b><small>Every supported answer includes a source quote.</small></span><span aria-hidden="true">→</span></button></section>
  </div>
}

function DocumentLibrary({ documents, busy, onSelect }: { documents: Document[]; busy: boolean; onSelect: (id: number) => void }) {
  const [search, setSearch] = useState('')
  const [lifecycle, setLifecycle] = useState('ALL')
  const filtered = documents.filter((document) => {
    const matchesText = `${document.title} ${document.rbi_ref || ''}`.toLowerCase().includes(search.trim().toLowerCase())
    return matchesText && (lifecycle === 'ALL' || (document.lifecycle_state || 'UNKNOWN') === lifecycle)
  })
  return <>
    <div className="page-heading"><div><p className="eyebrow">OFFICIAL RBI SOURCES</p><h1>Regulations<span className="heading-dot">.</span></h1><p className="subheading">Browse the curated corpus currently stored in this RAAY instance.</p></div><span className="corpus-status"><i /> {documents.length} documents</span></div>
    <div className="library-toolbar"><label className="search-field"><span className="sr-only">Search documents</span><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5" /></svg><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search title or RBI reference" /></label><label className="library-filter">Lifecycle<select value={lifecycle} onChange={(event) => setLifecycle(event.target.value)}><option value="ALL">All statuses</option><option value="IN_FORCE">In force</option><option value="REPEALED">Repealed</option><option value="SUPERSEDED">Superseded</option><option value="DRAFT">Draft</option></select></label></div>
    <div className="library-summary"><b>{filtered.length}</b> of {documents.length} documents <span>Each row opens verified document relationships and source evidence.</span></div>
    <div className="table-card"><div className="table-head"><span>DOCUMENT</span><span>RBI REFERENCE</span><span>STATUS</span><span>VERSION</span></div>{filtered.map((doc) => <button type="button" className="table-row" key={doc.id} onClick={() => onSelect(doc.id)}><span className="doc-name">{doc.title}<small>View document history and evidence <span aria-hidden="true">↗</span></small></span><span className="doc-ref">{doc.rbi_ref || '—'}</span><span><Lifecycle state={doc.lifecycle_state} /></span><span className="version-label">v{doc.version_no}</span></button>)}{filtered.length === 0 && <div className="table-empty">{busy ? 'Loading documents…' : 'No documents match these filters.'}</div>}</div>
    <p className="table-footnote"><span className="source-bullet"/> This is a curated, growing corpus. It is not a complete RBI search index.</p>
  </>
}

function DocumentCard({ doc, onClick }: { doc: RelevantDocument; onClick: () => void }) {
  const evidence = doc.evidence[0]
  return <article className="relevance-card">
    <button className="relevance-card-main" type="button" onClick={onClick} aria-label={`Open verified relationships for ${doc.title}`}>
      <div className="card-top"><span className={`match-badge ${doc.outcome.toLowerCase()}`}>{doc.outcome === 'DIRECT' ? 'DIRECT MATCH' : 'POTENTIAL MATCH'}</span><span className="card-arrow" aria-hidden="true">↗</span></div>
      <p className="card-ref">{doc.rbi_ref || 'RBI document'}</p><h3>{doc.title}</h3><div className="card-life"><Lifecycle state={doc.lifecycle_state} /></div>
    </button>
    {evidence && <div className="card-evidence"><blockquote>“{evidence.quote}”</blockquote><a href={evidence.source_url} target="_blank" rel="noreferrer">{evidence.page ? `PDF page ${evidence.page}` : evidence.dom_locator || 'Official RBI source'} ↗</a></div>}
  </article>
}

function ProfileScreen({ profile, setProfile, onSave, busy }: { profile: Profile; setProfile: (profile: Profile) => void; onSave: (event: FormEvent<HTMLFormElement>) => void; busy: boolean }) {
  function setAttribute(key: string, value: string) { setProfile({ ...profile, attributes: { ...profile.attributes, [key]: value } }) }
  return <><div className="page-heading"><div><p className="eyebrow">YOUR ORGANIZATION</p><h1>Business profile<span className="heading-dot">.</span></h1><p className="subheading">Used to match official RBI applicability evidence to your organization.</p></div></div><form className="form-card" onSubmit={onSave}><div className="form-section-title"><span className="step-index">01</span><div><h2>Regulated entity</h2><p>Choose the closest entity type. RAAY will not assume facts you have not provided.</p></div></div><label className="field-label" htmlFor="entity">Entity classification</label><select id="entity" value={profile.entity_code} onChange={(event) => setProfile({ ...profile, entity_code: event.target.value })}><option value="NBFC_MFI">NBFC — Microfinance Institution</option><option value="NBFC_ICC">NBFC — Investment and Credit Company</option><option value="NBFC">Other NBFC</option><option value="COMMERCIAL_BANK">Commercial Bank</option><option value="PAYMENTS_BANK">Payments Bank</option><option value="HFC">Housing Finance Company</option></select><div className="form-divider"/><div className="form-section-title"><span className="step-index">02</span><div><h2>Known business attributes</h2><p>Optional details help evaluate rules with explicit conditions.</p></div></div><div className="field-grid"><label className="field-label">Deposit taking<select value={profile.attributes.deposit_taking || ''} onChange={(event) => setAttribute('deposit_taking', event.target.value)}><option value="">Not specified</option><option value="true">Yes</option><option value="false">No</option></select></label><label className="field-label">Scale layer<select value={profile.attributes.layer || ''} onChange={(event) => setAttribute('layer', event.target.value)}><option value="">Not specified</option><option value="BASE">Base</option><option value="MIDDLE">Middle</option><option value="UPPER">Upper</option><option value="TOP">Top</option></select></label></div><div className="form-footer"><span>Profile data is private to your account.</span><button className="primary-button" disabled={busy}>{busy ? 'Saving…' : 'Save profile'} <span>→</span></button></div></form></>
}

function Explorer({ documents, selectedId, setSelectedId, selected, relations, loading }: { documents: Document[]; selectedId: number | null; setSelectedId: (id: number) => void; selected?: Document; relations: Relationship[]; loading: boolean }) {
  const verified = relations.filter((relation) => relation.verification_status === 'VERIFIED')
  return <>
    <div className="page-heading"><div><p className="eyebrow">TRACE THE RULE</p><h1>Relationship explorer<span className="heading-dot">.</span></h1><p className="subheading">See how official RBI documents connect, with the source text beside every verified link.</p></div></div>
    <div className="explorer-intro"><span className="explorer-intro-icon"><Icon name="explorer" /></span><p><b>How to use this view</b><br />Choose a document to see verified amendments, replacements, or repeals. Open the RBI citation to check the original wording.</p></div>
    <DocumentPicker documents={documents} selectedId={selectedId} onChange={setSelectedId} />
    <div className="explorer-layout"><section className="explorer-main">
      {selected ? <>
        <div className="document-title-card"><div><span className="card-ref">{selected.rbi_ref || selected.source_key}</span><h2>{selected.title}</h2></div><Lifecycle state={selected.lifecycle_state} /></div>
        {selected.lifecycle_state === 'REPEALED' && <aside className="repeal-note"><b>What “repealed” means</b><p>RBI has withdrawn this instrument from legal force. A business needs this status to avoid relying on an obsolete rule and to check whether another current direction replaced it. Repeal does not, by itself, prove a replacement; follow only the verified links below.</p><small>RAAY shows source status and evidence. It does not decide your legal obligations.</small></aside>}
        <div className="timeline-label"><span>VERIFIED RELATIONSHIP HISTORY</span><span>{verified.length} {verified.length === 1 ? 'LINK' : 'LINKS'}</span></div>
        {loading ? <div className="loading-card"><span className="spinner"/><span>Looking up verified relationships…</span></div> : verified.map((relation) => <article className="relation-card" key={relation.id}>
          <div className="relation-top"><span className="relation-type">{relation.relation_type.replaceAll('_', ' ')}</span><span className="verified"><i /> VERIFIED</span></div>
          <h3>{relation.direction === 'OUTGOING' ? relation.target_title || relation.target_ref_raw : relation.source_title}</h3>
          {relation.target_clause && <p className="clause-ref">Clause {relation.target_clause}</p>}
          <blockquote>“{relation.evidence_text}”</blockquote>
          <a className="source-link" href={relation.source_url} target="_blank" rel="noreferrer">{relation.evidence_page ? `PDF page ${relation.evidence_page}` : relation.evidence_dom_locator || 'Official RBI source'} ↗</a>
          {relation.old_text || relation.new_text ? <div className="diff-box"><span className="eyebrow">AVAILABLE TEXT CHANGE</span>{relation.old_text && <p className="old-text">− {relation.old_text}</p>}{relation.new_text && <p className="new-text">+ {relation.new_text}</p>}{!relation.old_text || !relation.new_text ? <p className="muted-label">A complete historical pair is not available yet.</p> : null}</div> : <p className="muted-label diff-missing">No verified old/new clause pair is stored for this relationship.</p>}
        </article>)}
        {!loading && verified.length === 0 && <div className="empty-card relation-empty"><span className="empty-icon"><Icon name="explorer" /></span><div><h3>No verified links in this document</h3><p>RAAY hides unresolved references. Similar wording alone is not enough to prove a legal relationship.</p></div></div>}
      </> : <div className="empty-card"><p>Select an RBI document to inspect its verified links.</p></div>}
    </section><aside className="explorer-aside"><span className="eyebrow">THE EVIDENCE STANDARD</span><h3>Every relationship has a source.</h3><p>Only verified, quote-backed links appear here. Similarity alone never establishes an amendment or repeal.</p><div className="aside-rule"/><span className="verified"><i /> VERIFIED FROM RBI TEXT</span></aside></div>
  </>
}

function QuestionScreen({ documents, selectedId, setSelectedId, question, setQuestion, onAsk, answer, busy, elapsedSeconds }: { documents: Document[]; selectedId: number | null; setSelectedId: (id: number) => void; question: string; setQuestion: (question: string) => void; onAsk: (event: FormEvent<HTMLFormElement>) => void; answer: Answer | null; busy: boolean; elapsedSeconds: number }) {
  const selected = documents.find((document) => document.id === selectedId)
  const sample = selected?.rbi_ref === 'RBI/2025-26/44'
    ? 'According to paragraph 8.1, what minimum percentage of total assets must be qualifying assets?'
    : 'What is the main requirement in this document?'
  return <>
    <div className="page-heading"><div><p className="eyebrow">GROUNDED QUESTION ANSWERING</p><h1>Ask RAAY<span className="heading-dot">.</span></h1><p className="subheading">Ask in plain language. Get an answer you can trace to official RBI text.</p></div></div>
    <div className="question-layout"><div className="question-main">
      <div className="question-intro"><span className="question-intro-icon"><Icon name="questions" /></span><div><b>Start with a document</b><p>RAAY searches the selected document and its verified relationship scope.</p></div></div>
      <DocumentPicker documents={documents} selectedId={selectedId} onChange={setSelectedId} />
      <div className="question-examples"><span>TRY AN EXAMPLE</span><button type="button" onClick={() => setQuestion(sample)}>{sample}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M8 7h9v9" /></svg></button></div>
      <form className="question-form" onSubmit={onAsk}>
        <label className="field-label" htmlFor="question">Your question</label>
        <textarea id="question" rows={4} minLength={3} maxLength={2000} required value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about a requirement, threshold, date, or entity…" />
        <div className="question-footer"><span>Answers use only retrieved clauses from the selected RBI scope.</span><button className="primary-button" disabled={busy || !selectedId}>{busy ? <><span className="button-spinner"/> Searching evidence</> : <>Ask RAAY <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6" /></svg></>}</button></div>
      </form>
      {busy && <div className="request-progress" role="status" aria-live="polite"><span className="spinner"/><div><b>Finding and checking your answer</b><p>RAAY is searching clauses, drafting from the retrieved text, and checking its citations. {elapsedSeconds > 0 ? `Elapsed: ${elapsedSeconds}s.` : ''}</p><small>The local model may take longer on its first request while it loads.</small></div></div>}
      {answer && <section className={`answer-card ${answer.insufficient_evidence ? 'insufficient' : ''}`} aria-live="polite"><div className="answer-label"><span className="answer-mark">{answer.insufficient_evidence ? '!' : '✓'}</span>{answer.insufficient_evidence ? 'NOT ENOUGH SOURCE EVIDENCE' : 'ANSWER · SOURCE VERIFIED'}</div><p className="answer-text">{answer.answer}</p>{answer.claims.map((claim, index) => <article className="claim-card" key={`${claim.clause_id}-${index}`}><p>{claim.text}</p><blockquote><span>Source quote</span>“{claim.quote}”</blockquote><a className="source-link" href={claim.source_url} target="_blank" rel="noreferrer">Open RBI source <span aria-hidden="true">↗</span></a><div className="citation-meta"><span>{claim.document_title}</span><span>§ {claim.path}{claim.page ? ` · Page ${claim.page}` : claim.dom_locator ? ` · ${claim.dom_locator}` : ''}</span></div></article>)}</section>}
    </div>
      <aside className="question-aside"><span className="eyebrow">HOW AN ANSWER IS BUILT</span><div className="answer-step"><span>01</span><div><b>Find relevant clauses</b><p>Search selected documents and verified links.</p></div></div><div className="answer-step"><span>02</span><div><b>Draft from evidence</b><p>The local model receives retrieved RBI text only.</p></div></div><div className="answer-step"><span>03</span><div><b>Check the quote</b><p>Each answer claim must match its cited clause.</p></div></div><div className="aside-rule"/><p className="muted-label">No matching source quote means no supported answer.</p></aside>
    </div>
  </>
}

function DocumentPicker({ documents, selectedId, onChange }: { documents: Document[]; selectedId: number | null; onChange: (id: number) => void }) {
  return <label className="document-picker"><span className="field-label">Document scope</span><select value={selectedId || ''} onChange={(event) => onChange(Number(event.target.value))}><option value="" disabled>Select a document</option>{documents.map((document) => <option key={document.id} value={document.id}>{document.rbi_ref ? `${document.rbi_ref} — ` : ''}${document.title}</option>)}</select></label>
}

function Lifecycle({ state }: { state: string | null }) {
  const value = state || 'UNKNOWN'
  return <span className={`lifecycle lifecycle-${value.toLowerCase()}`}><i />{value.replaceAll('_', ' ')}</span>
}
