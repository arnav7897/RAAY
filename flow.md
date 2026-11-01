# flow.md — What RAAY Has Built So Far

This document shows only behavior implemented in code so far. The complete target architecture remains in [`README.md`](README.md) and [`plan.md`](plan.md). New implemented behavior is added phase by phase so the build history stays easy to follow.

**Last updated:** 2026-11-01  
**Current phase:** Phase 4 in progress — scoped FTS and live Gemini citation path accepted; semantic retrieval remains

Status legend: `Done` means implemented and checked · `In progress` means code exists but the phase acceptance path is incomplete

---

## 1. Current implementation

```mermaid
flowchart LR
  RBI[RBI official listings] --> SCH[APScheduler worker]
  SCH --> DIS[Allowlisted title keyword discovery]
  DIS --> FET[Polite fetch and raw cache]
  GOLD[Locked gold URLs] --> FET
  FET --> PAR[HTML or PDF parser]
  PAR --> VER[Immutable document versions and clauses]
  VER --> DB[(PostgreSQL and pgvector)]
  DB --> API[FastAPI document and clause endpoints]

  VER --> REF[Reference extraction]
  REF --> CLS[Explicit verb classification]
  CLS --> RSV[Alias or title and date resolution]
  RSV --> QV[Quote span validation]
  QV --> DIF[Sentence diff and repeal row parsing]
  QV --> RDB[Idempotent relationship persistence]
  RDB --> DB
  WLIST[Official withdrawn-circular table] --> WPARSE[Parse reference, title, date, and DOM evidence]
  WPARSE --> WRES[Resolve exact corpus aliases]
  WRES --> RDB
  DB --> RAPI[FastAPI relationship evidence endpoint]
  VER --> AF[Deterministic addressee extraction]
  AF --> ADB[Applicability facts]
  ADB --> DB
  DB --> LC[Lifecycle computation from verified edges]
  Q[Question and selected document IDs] --> SR[Scoped FTS retrieval]
  RDB --> SR
  SR --> RRF[Rank clauses with reciprocal-rank fusion seam]
  RRF --> GEM[Gemini Interactions API with store=false]
  GEM --> CV[Validate Pydantic claims and exact source quotes]
  CV --> ANS[Cited claims or insufficient evidence]
  ANS --> API
```

The ingestion, relationship, applicability, and lifecycle paths run end to end. Old-versus-new diff persistence remains empty until both texts come from reproducible official RBI artifacts.

---

## 2. Phase 0 additions — foundation and source lock

### Implemented

- Docker Compose database, API, and worker services.
- PostgreSQL 16 with pgvector.
- Six source-locked official RBI gold documents in `data/gold/corpus.yaml`.
- Environment contracts for RBI polling, Auth0, Gemini, and embeddings.
- Initial database schema and repository layout.

---

## 3. Phase 1 additions — discovery, ingestion, versioning, and parsing

```mermaid
flowchart TD
  T[Scheduled or manual source run] --> L[Fetch official RBI listing]
  L --> K[Match configured title keywords]
  K --> A[Allow only known RBI detail endpoints]
  A --> C[Cap matches per source]
  C --> F[Fetch with one second minimum spacing]
  F --> R[Cache raw response]
  R --> P{Source format}
  P -- HTML --> H[Parse clauses with DOM locations]
  P -- PDF --> D[Parse clauses with page locations]
  H --> S[Normalized SHA-256]
  D --> S
  S --> N{Hash changed}
  N -- no --> U[Record unchanged run]
  N -- yes --> V[Create immutable version and clauses]
  U --> I[(ingest_runs)]
  V --> I
```

### Implemented and checked

- Fixed gold-corpus ingestion.
- Live discovery from RBI drafts, notifications, Master Directions, and withdrawn-circular listings.
- Title keyword configuration, official endpoint allowlist, stable URL keys, and per-source match cap.
- Drafts and notifications every three hours on weekdays; Master Directions and withdrawn circulars daily.
- Robots policy checks, descriptive user agent, minimum one-second request spacing, and raw caching.
- HTML-first parsing with PDF fallback.
- Normalized offsets plus HTML DOM or PDF page evidence locations.
- Immutable document versions and idempotent reruns.
- `GET /health`, `GET /documents`, and `GET /documents/{id}/clauses`.
- Every run audited in `ingest_runs`.

---

## 4. Phase 2 additions — relationship engine so far

```mermaid
flowchart TD
  TXT[Parsed regulatory text] --> ID[Extract RBI and department IDs]
  TXT --> TITLE[Extract titled and dated references]
  TXT --> CTX[Extract ibid and dated circular references]
  ID --> RES[Resolve exact aliases first]
  TITLE --> FUZ[Resolve title similarity at least 92 plus exact date]
  CTX --> UNR[Keep unresolved until context is proven]
  RES --> VERB[Classify explicit legal verb]
  FUZ --> VERB
  VERB --> SPAN[Validate quote in source text]
  SPAN --> DIFF[Prepare normalized sentence diff]
  TXT --> REP[Parse repeal annex rows]
```

### Implemented and unit-tested

- RBI and departmental reference extraction with source spans.
- Titled Master Direction, publication-date, target-clause, `ibid`, and dated-circular extraction.
- Table-driven classification for amended, substituted, inserted, deleted, omitted, replaced, repealed, withdrawn, superseded, and consolidated relationships.
- Negative rules preventing phrases such as “as amended from time to time” from creating edges.
- Resolution order: exact alias, then title similarity of at least 92 with an exact publication date, otherwise unresolved.
- Unicode and whitespace-normalized quote-span validation.
- Sentence-level old/new diff preparation.
- Deterministic repeal-annex row parsing.
- Adjacent evidence paragraphs are combined when a reference and its legal instruction span separate HTML or PDF blocks.
- Additive `document_relations` and `clause_versions` schema with an explicit rollback script.
- Pull-based `python -m app.relations.run` reconciliation with audited runs and idempotent upserts.
- Missing raw files are reported and skipped without blocking valid source documents.
- Unchanged ingestion backfills missing raw-cache metadata without creating another document version.
- `GET /documents/{id}/relations` returns incoming and outgoing evidence, verification status, source location, and available diff fields.
- Live verification persisted 251 unique rows across the current local corpus: one explicit `VERIFIED AMENDS` edge and 250 `CANDIDATE RELATED_TO` references. A second run kept the row count at 251.

### Current Phase 2 boundary

The official RBI historical artifact containing the earlier paragraph 8.1 is still unavailable locally. Therefore `old_text`, `new_text`, and the persisted diff for RBI/2025-26/44 remain incomplete, and Phase 2 acceptance has not passed.

---

## 5. Phase 3 additions — lifecycle and applicability so far

```mermaid
flowchart TD
  DOC[Parsed official document] --> ADDR[Recognized addressee or applicability clause]
  ADDR --> FACT[Includes or excludes fact with evidence location]
  FACT --> ONT[Entity ontology subsumption]
  PROFILE[Entity code and conditions] --> ONT
  ONT --> EX{Matching exclusion}
  EX -- yes --> NO[NOT ESTABLISHED]
  EX -- no --> COND{Conditions established}
  COND -- yes --> DIRECT[DIRECT]
  COND -- no --> POTENTIAL[POTENTIAL]

  REL[Verified relationships] --> LIFE[Lifecycle precedence]
  LIFE --> STATE[Draft in force repealed or superseded]
```

### Implemented and checked

- Entity ontology for banks, co-operative banks, NBFCs, NBFC-ICC, NBFC-MFI, HFC, and bank subtypes.
- Subsumption matching, such as `NBFC_MFI` satisfying an `NBFC` inclusion.
- Exclusions override inclusions; unmet or absent conditions never produce `DIRECT`.
- Sixteen table-driven profile×fact cases plus lifecycle precedence tests.
- Deterministic addressee extraction with HTML DOM or PDF page evidence locations.
- Additive `entity_ontology` and `applicability_facts` schema with explicit rollback.
- Audited `python -m app.applicability.run` reconciliation with idempotent upserts.
- Live run stored 12 official facts; the second run kept the row count at 12.
- RBI/2025-26/44 stored `NBFC_MFI INCLUDES` with the official addressee and DOM locator.
- Audited `python -m app.lifecycle.run` computes state only from dates and verified relationships.
- Official withdrawn-circular table parsing stores exact reference, title, date, DOM location, offsets, and source URL.
- Exact corpus aliases from the table create idempotent `VERIFIED REPEALS` edges; unknown rows remain outside the narrow corpus.
- Live lifecycle reconciliation marks 4 documents `REPEALED` and 7 `IN_FORCE`.
- RBI/2025-26/44 is `REPEALED` from official withdrawal evidence.

### Phase 3 acceptance

An NBFC-MFI matches RBI/2025-26/44 as `DIRECT`, while NBFC-ICC is `NOT_ESTABLISHED`. The document is `HISTORICAL — repealed` because the official withdrawal table proves repeal. It is not labelled consolidated because no official evidence names a consolidation target.

---

## 6. Phase 4 additions — scoped retrieval and grounded answers so far

### Implemented

- `POST /questions` accepts a question and explicit document IDs.
- Retrieval expands scope up to one hop using verified relationships only, then searches current-version clauses with PostgreSQL full-text search.
- Reciprocal-rank fusion combines lexical and semantic rankings when semantic retrieval is available; embeddings remain unimplemented.
- Gemini Interactions adapter sends structured Pydantic JSON Schema with `store=false`.
- Claim validation requires a retrieved clause ID and a quote found in that clause; responses include page or DOM location and official source URL.
- Unsupported results return `Insufficient evidence in the selected documents`.
- Fallback diagnostics distinguish empty retrieval, empty model output, empty model claims, and rejected citations without logging prompts or quotes.
- Gemini's configured 30-second timeout is converted to the SDK's required milliseconds.

### Current Phase 4 boundary

Live retrieval returned paragraph 8.1 from RBI/2025-26/44 and the related 2022 direction. After changing query matching and converting the configured timeout to SDK milliseconds, the live API returned the 60 percent requirement with a matching quote and HTML DOM locator. Core lexical retrieval and grounded-answer acceptance pass. Semantic retrieval and remaining Phase 4 edge cases remain. See D-050 through D-052.

---

## 7. Current Docker Compose runtime

```mermaid
flowchart LR
  W[Worker container] --> RBI[RBI official sources]
  W --> RAW[Shared raw cache]
  W --> DB[(PostgreSQL and pgvector)]
  API[API container] --> DB
  DEV[Developer or API client] --> API
```

Running services today are `db`, `api`, and `worker`. Applicability and lifecycle run as pull-based worker commands. There is no implemented frontend, Auth0 verification, Gemini adapter, or retrieval engine yet, so those components are intentionally absent.

---

## 8. Build change log

| Date | Phase | Addition | Decision |
|------|-------|----------|----------|
| 2026-11-01 | Planning | Evidence-first architecture, Auth0 contract, Compose runtime, Gemini provider | D-022 to D-035 |
| 2026-11-01 | Phase 1 | Normalized version hashes and source ordinals | D-036, D-037 |
| 2026-11-01 | Phase 1 | Host database port and source identity validation | D-038, D-039 |
| 2026-11-01 | Phase 1 | Allowlisted keyword discovery and capped polling | D-040 |
| 2026-11-01 | Phase 1 | APScheduler cadence and worker bootstrap | D-041 |
| 2026-11-01 | Phase 2 | Official historical artifact required for old/new evidence | D-042 |
| 2026-11-01 | Documentation | `flow.md` changed to current-only, phase-by-phase implementation history | D-043 |
| 2026-11-01 | Phase 2 | Idempotent relationship reconciliation, persistence, and evidence API | D-044 |
| 2026-11-01 | Phase 2 | Unchanged ingestion repairs missing raw-cache metadata | D-045 |
| 2026-11-01 | Phase 2 | Historical diff deferred without treating alternate test as official proof | D-046 |
| 2026-11-01 | Phase 3 | Ontology matching, exclusions, conditions, and applicability persistence | D-047 |
| 2026-11-01 | Phase 3 | Lifecycle changes require verified relationship evidence | D-048 |
| 2026-11-01 | Phase 3 | Official withdrawal rows create verified repeal edges without inferring consolidation | D-049 |
| 2026-11-01 | Phase 4 | Scoped retrieval, Gemini structured claims, quote validation, and fallback diagnostics | D-050 |
| 2026-11-01 | Phase 4 | Convert configured Gemini timeout seconds to SDK milliseconds | D-051 |
| 2026-11-01 | Phase 4 | Live grounded answer returns a verified clause quote and source location | D-052 |
