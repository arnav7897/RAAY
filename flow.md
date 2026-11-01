# flow.md — Current Architecture and Build Status

Living document. It shows what is designed and what has actually been built. Update it at the end of every phase and whenever the architecture changes.

**Last updated:** 2026-11-01 · **Current phase:** Phase 1 in progress; ingestion core accepted, scheduled discovery pending

Status legend: `Planned` means designed only · `In progress` means implementation has started · `Done` means the acceptance check passed · `Changed` means the implementation differs from the plan and has a decision entry

---

## 1. Overall architecture with build status

```mermaid
flowchart LR
  AU[Auth0 Universal Login] --> FE[React frontend]
  FE --> API[FastAPI]
  API --> USR[Profile and applicability]
  API --> GRA[Verified relationship graph]
  API --> RET[Staged retrieval]
  RET --> GEM[Gemini adapter]
  GEM --> VAL[Claim and quote validator]
  VAL --> FE

  RBI[RBI official sources] --> WRK[Scheduled ingestion worker]
  WRK --> PAR[Parse and version]
  PAR --> VER[Deterministic verification]
  VER --> KB[(PostgreSQL and pgvector)]
  KB --> USR
  KB --> GRA
  KB --> RET

  classDef planned fill:#eeeeee,stroke:#888,color:#222;
  classDef wip fill:#fff3cd,stroke:#b58900,color:#222;
  classDef done fill:#d4edda,stroke:#2e7d32,color:#222;
  class AU,FE,USR,GRA,RET,GEM,VAL planned;
  class API,WRK wip;
  class RBI,PAR,VER,KB done;
```

The gold ingestion, immutable versioning, parsing and database path are implemented. Authentication, relevance, retrieval, Gemini and the product frontend remain planned.

## 2. Component status

| Component | Phase | Status | Notes or acceptance |
|-----------|-------|--------|---------------------|
| Docker Compose foundation | 0 | In progress | Database and API validated; frontend not created yet |
| Auth0 authentication contract | 0 | Planned | Issuer, audience, JWKS and PKCE configuration documented |
| Gold corpus and labelled pairs | 0 | In progress | Six official URLs and hashes locked; labelled pairs pending |
| Scheduler and source discovery | 1 | Planned | Idempotent polling and recorded ingest runs |
| Immutable document versioning | 1 | Done | Normalized hashes; immediate six-source rerun created zero versions |
| HTML and PDF clause parsing | 1 | Done | All configured gold clauses found; HTML live and PDF unit tests pass |
| Document and clause read API | 1 | Done | Health, document list and latest clause-tree endpoints smoke-tested |
| Reference extraction | 2 | Planned | Identifier and amendment patterns tested |
| Relationship resolution and verification | 2 | Planned | RBI/2025-26/44 AMENDS paragraph 8.1 with verified evidence |
| Lifecycle engine | 3 | Planned | State and derived historical labels tested |
| Applicability engine and ontology | 3 | Planned | Exclusion and subsumption tests pass |
| Embedding reconciliation | 4 | Planned | BGE-M3 vectors stored separately from clauses |
| Staged retrieval | 4 | Planned | Eligible documents, graph, section and clause stages enforced |
| Gemini adapter | 4 | Planned | Stateless structured output and local Pydantic validation |
| Claim and quote validation | 4 | Planned | Unsupported or fabricated claims are rejected |
| Authenticated profile isolation | 5 | Planned | Cross-user access attempts are rejected |
| Frontend and Relationship Explorer | 5 | Planned | Evidence panel and old-versus-new diff work |
| Evaluation and demo | 6 | Planned | `EVAL.md` reports real counts and failures |

## 3. Docker Compose runtime

```mermaid
flowchart TB
  B[Browser] --> F[Frontend container]
  F --> A[API container]
  A --> D[(PostgreSQL with pgvector)]
  A --> X[Auth0 JWKS and token verification]
  A --> M[Gemini Interactions API]
  W[Worker container] --> D
  W --> R[RBI official sources]
  W --> C[Raw response cache]
```

Auth0 and Gemini are external managed services. Gemini uses `GEMINI_API_KEY`, `GEMINI_EXTRACT_MODEL=gemini-3.8-flash`, and `GEMINI_ANSWER_MODEL=gemini-3.8-flash`. Secrets and tenant values come from environment variables. PostgreSQL is not exposed directly to the browser.

## 4. Ingestion and versioning flow

```mermaid
flowchart TD
  S[Scheduled trigger] --> L[Fetch official RBI listing]
  L --> N{Known URL and unchanged hash}
  N -- yes --> X[Record no change]
  N -- no --> F[Fetch and cache source]
  F --> V[Create immutable document version]
  V --> H{HTML text available}
  H -- yes --> P1[Parse HTML with DOM locations]
  H -- no --> P2[Parse PDF with page locations]
  P2 --> O{Usable text layer}
  O -- no --> OCR[Run OCR only when required]
  O -- yes --> C[Build clause tree]
  OCR --> C
  P1 --> C
  C --> R[Extract references and amendment verbs]
  R --> E{Target resolved and explicit verb found}
  E -- yes --> VR[Create VERIFIED edge with evidence]
  E -- unresolved target --> UR[Store UNRESOLVED reference]
  E -- no explicit verb --> CA[Store CANDIDATE]
  VR --> LC[Recompute lifecycle]
  C --> DB[(PostgreSQL)]
  VR --> DB
  UR --> DB
  CA --> DB
  LC --> DB
```

PDF evidence stores a page; HTML evidence stores a DOM locator. Both store normalized offsets, source URL, quote, extractor and extractor version.

## 5. Authenticated user request flow

```mermaid
flowchart TD
  U[User] --> AU[Auth0 Universal Login with PKCE]
  AU --> T[Access token]
  T --> JV[Verify signature issuer audience and expiry]
  JV --> IM[Map subject to internal user]
  IM --> P[Load only owned profile]
  P --> A1[Eligible documents by applicability and lifecycle]
  A1 --> A2[Expand verified graph up to two hops]
  A2 --> A3[Filter sections]
  A3 --> A4[Hybrid clause retrieval]
  A4 --> GM[Gemini structured response]
  GM --> PV[Pydantic validation]
  PV --> QV{Every quote exists in cited clause}
  QV -- yes --> OK[Cited answer]
  QV -- no claims survive --> NO[Insufficient evidence]
```

The browser never supplies the effective user ID. Gemini receives only retrieved corpus clauses, uses `store=false`, and has no Search grounding or URL Context.

## 6. Relationship proof and lifecycle flow

```mermaid
flowchart LR
  SRC[Explicit source instruction] --> EXT[Extract reference verb and quote]
  EXT --> ALI[Resolve document alias]
  ALI --> TGT[Target document version and clause]
  SRC --> NEW[New clause text]
  TGT --> OLD[Historical target text]
  OLD --> DIF[Normalized sentence diff]
  NEW --> DIF
  DIF --> REC[Verified relation with evidence]
  REC --> EVT[Lifecycle event]
  EVT --> STA[DRAFT IN_FORCE REPEALED or SUPERSEDED]
  REC --> LAB[Derived amended or consolidated label]
```

Amendment and consolidation remain relationships. They are not stored as mutually exclusive lifecycle states.

## 7. Pull-based reconciliation

```mermaid
flowchart LR
  KB[(New or changed clauses)] --> AP[Applicability reconcile job]
  KB --> EM[Embedding reconcile job]
  AP --> AF[Missing applicability facts]
  EM --> CE[Missing BGE-M3 embeddings]
  AF --> KB
  CE --> KB
```

Reconciliation jobs find missing outputs and are safe to rerun. Ingestion does not call applicability, embedding or retrieval modules directly.

## 8. Change log

| Date | Change | Related decision |
|------|--------|------------------|
| 2026-11-01 | Initial architecture designed; no code written | D-001 to D-018 |
| 2026-11-01 | Separate embeddings and pull-based reconciliation introduced | D-019 to D-021 |
| 2026-11-01 | Evidence-first authenticated MVP, Auth0 and Docker Compose selected | D-022 to D-024 |
| 2026-11-01 | Gold-first scheduled polling and Gemini structured-output adapter selected | D-025 to D-028 |
| 2026-11-01 | Authenticated ownership, immutable versions and source-specific evidence locations added | D-029 to D-031 |
| 2026-11-01 | Lifecycle representation, embedding storage and single-workstream flow corrected | D-032 to D-034 |
| 2026-11-01 | Official RBI sources made mandatory for stored evidence | D-035 |
| 2026-11-01 | Phase 1 ingestion core implemented with normalized hashing and source ordinals | D-036, D-037 |
| 2026-11-01 | Non-conflicting database port and mandatory source identity validation added | D-038, D-039 |
