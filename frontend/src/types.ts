export type Document = {
  id: number
  source_key: string
  rbi_ref: string | null
  title: string
  published_at: string | null
  effective_at: string | null
  lifecycle_state: string | null
  source_url: string
  version_no: number
  content_hash: string
}

export type Evidence = {
  quote: string
  page: number | null
  dom_locator: string | null
  source_url: string
}

export type RelevantDocument = {
  id: number
  rbi_ref: string | null
  title: string
  lifecycle_state: string | null
  source_url: string
  outcome: 'DIRECT' | 'POTENTIAL'
  reasons: string[]
  evidence: Evidence[]
}

export type Relationship = {
  id: number
  direction: 'OUTGOING' | 'INCOMING'
  source_title: string
  target_title: string | null
  target_ref_raw: string
  target_clause: string | null
  relation_type: string
  evidence_text: string
  evidence_page: number | null
  evidence_dom_locator: string | null
  source_url: string
  verification_status: string
  old_text: string | null
  new_text: string | null
  diff: { operation: string; old_text: string; new_text: string }[]
}

export type Answer = {
  answer: string
  insufficient_evidence: boolean
  claims: {
    clause_id: number
    text: string
    quote: string
    document_id: number
    document_title: string
    path: string
    page: number | null
    dom_locator: string | null
    source_url: string
  }[]
}

export type Profile = { entity_code: string; attributes: Record<string, string> }
