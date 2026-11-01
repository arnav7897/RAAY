# decision.md — Design Decision Log

Records important design decisions and **why** they were made. Append only: never delete an entry. With two people, new entries use `D-A01…` (Person A) or `D-B01…` (Person B); `D-001` to `D-021` are shared history. If a decision changes, add a new entry and mark the old one `Superseded by D-xxx`.

Status values: `Accepted` · `Provisional` (needs a test or answer) · `Superseded`.

**Current project status:** Phase 1 in progress; ingestion, live keyword discovery and periodic polling are implemented, while Phase 0 labelled pairs remain pending.

---

## Core principles

### D-001 — LLMs propose, deterministic code verifies
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** An LLM may suggest candidate references or evidence. Only rule-based code may create a `VERIFIED` relationship.
- **Why:** Two documents can sound similar without being legally related. Wrong amendment links are worse than missing ones in a compliance product.
- **Rejected:** Letting an LLM or embedding similarity decide relationships.

### D-002 — Three separate relevance problems
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Treat document-to-document, document-to-stakeholder and clause-to-stakeholder relevance as separate logic.
- **Why:** One combined embedding search produces false positives (an amendment about NBFC-MFIs would be shown to every NBFC).

### D-003 — Evidence hierarchy and relationship types
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Relationship types: `AMENDS`, `REPLACES`, `REPEALS`, `CONSOLIDATED_INTO`, `IMPLEMENTS`, `RELATED_TO`. The first four need explicit text (amendment instruction or repeal list). Semantic similarity can only create `CANDIDATE`, shown as "Potentially related, not officially verified".
- **Why:** Authoritative relationships must be traceable to official wording.

### D-004 — Evidence must be a verbatim quote with location
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Every `VERIFIED` edge stores quote, page, character offsets, URL, extractor and version. Any LLM-provided quote must exist in the source after normalisation, or it is discarded.
- **Why:** Makes every claim independently checkable and blocks hallucinated evidence.

## Regulatory domain

### D-005 — Add a lifecycle / supersession layer
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Documents carry `IN_FORCE`, `AMENDED`, `REPEALED`, `CONSOLIDATED_INTO` status with validity dates.
- **Why:** On 28 Nov 2025 RBI consolidated its instructions into 244 Master Directions and withdrew thousands of circulars. The 2022 Microfinance Directions and RBI/2025-26/44 are now historical, so "AMENDS" alone would mislead users.

### D-006 — Two ID schemes handled with an alias table
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Store `RBI/2025-26/44` and department numbers like `DoR.FIN.REC.25/03.10.038/2025-26` in `document_aliases`. Resolution order: exact alias, then fuzzy title plus date, else `UNRESOLVED`.
- **Why:** Documents cite each other inconsistently. Guessing a target would create false edges.

### D-007 — Entity ontology with subsumption; no numeric relevance score
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Applicability uses an entity hierarchy (NBFC contains NBFC-MFI, layers) and outputs `DIRECT / POTENTIAL / NOT_ESTABLISHED`. Exclusions always override.
- **Why:** "All NBFCs" must match an MFI but an MFI-only circular must not match other NBFCs. A score like 92% implies false precision and can outrank an exclusion.

### D-008 — Small gold corpus, not the whole RBI site
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Build on about six verified documents plus a small seeded catalogue. Evaluate with 10 to 20 hand-labelled pairs and report counts, not general accuracy.
- **Why:** 12-hour budget. A narrow, provably correct system beats a wide, unverifiable one.

## Architecture

### D-009 — Modular monolith with a separate ingestion worker
- **Date:** 2026-11-01 · **Status:** Accepted
- **Why:** Multiple autonomous agents add coordination overhead with no benefit in a 12-hour build.

### D-010 — PostgreSQL with pgvector and full-text search; no graph database
- **Date:** 2026-11-01 · **Status:** Accepted
- **Why:** Small graph; recursive SQL handles relationship chains. One datastore keeps setup simple.

### D-011 — One global knowledge base; users only hold a profile
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** All documents are ingested once into a shared store. Per-user data is the profile, cached results and drafts. Applicability facts are precomputed per document and joined with the profile at query time.
- **Why:** RBI documents are public and identical for everyone; per-user parsing would be slow and costly.

### D-012 — Parse RBI HTML first, PDF as fallback
- **Date:** 2026-11-01 · **Status:** Accepted
- **Why:** RBI notification pages provide clean text, which avoids OCR and speeds up parsing. PDF/OCR only when HTML is missing.

### D-013 — Staged (hierarchical) retrieval instead of flat RAG
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Eligible documents (applicability + lifecycle), then graph expansion (up to 2 hops over verified edges), then section filter, then clause-level hybrid search (full-text + embeddings).
- **Why:** Flat top-k ignores document structure and the verified graph, and mixes unrelated or repealed documents. LLM-built graphs rejected because edges must be deterministic.

### D-014 — Scheduled ingestion by polling listing pages
- **Date:** 2026-11-01 · **Status:** Provisional
- **Decision:** Poll drafts and notifications every 3 hours on weekdays; Master Directions and withdrawn circulars daily. One idempotent CLI entry point.
- **Open:** RSS feed URLs not confirmed; verify in Phase 0.

## Models

### D-015 — Embeddings: BGE-M3 default, 1024-d, local
- **Date:** 2026-11-01 · **Status:** Provisional
- **Why:** Free, MIT licence, long context, dense + sparse in one model. Alternatives: Qwen3-Embedding-0.6B, nomic-embed-text-v2-moe, EmbeddingGemma.
- **Open:** Confirm with a 20-query recall@5 test on gold clauses; switch via `EMBEDDING_MODEL` if another wins. Model name stored per row.

### D-016 — LLM behind a single interface; hosted small and larger models with local fallback
- **Date:** 2026-11-01 · **Status:** Provisional
- **Why:** Avoids provider lock-in; LLM runs only on candidate spans and answers, keeping cost low.
- **Open:** Budget decision (hosted vs fully local default).

### D-017 — User profile free text is confirmed by the user
- **Date:** 2026-11-01 · **Status:** Accepted
- **Why:** A wrong silent inference about entity type would produce wrong applicability results.

## Tooling

### D-018 — Codex instructions kept in `codex.md`, copied to `AGENTS.md`
- **Date:** 2026-11-01 · **Status:** Accepted
- **Why:** Codex loads `AGENTS.md` by default. Context7 is used only for library documentation, never for RBI facts.

### Team and workflow

### D-019 — Embeddings stored in a separate table owned by the retrieval side
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** `clause_embeddings(clause_id, model, embedding)` replaces embedding columns on `clauses`.
- **Why:** Keeps the evidence engine's `clauses` table stable when the embedding model changes, lets several models coexist for the recall test, and removes a write conflict between two people.

### D-020 — Two-person split at the KB boundary with one-way dependency
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Person A owns what goes into the KB, Person B owns what comes out. B reads A's tables; A never imports B; B never writes A's tables. Contracts (schema, fixtures, OpenAPI) are frozen in Hour 0–1. Details in `team.md`.
- **Why:** Independent work with no merge or runtime coupling; each person can develop and test on fixtures.
- **Rejected:** Splitting by phase (A does phases 1 to 3, B does 4 to 6), which would leave B blocked until A finishes.

### D-021 — Pull-based reconcile jobs instead of cross-calls
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Embedding and applicability extraction run as idempotent jobs that find rows missing their output. The scheduler runs the ingest job, then `make reconcile`. No ingest code calls retrieval or applicability code.
- **Why:** Removes code coupling between the two owners and makes each job safely re-runnable.

---

### D-022 — Evidence-first authenticated MVP
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Build a narrow, evidence-first MVP with full authentication. Defer comment drafting, alerts, broad RBI crawling and cloud deployment.
- **Why:** Verified relationships, lifecycle, applicability and cited answers are the product proof. Authentication is required for real profile isolation, while the deferred features do not strengthen that proof.
- **Rejected:** Expanding corpus breadth or adding engagement features before the evidence path works end to end.
- **Open:** None; further scope cuts must not remove authentication or evidence validation.

### D-023 — Auth0 managed OIDC
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Use Auth0 Universal Login with Authorization Code and PKCE. FastAPI verifies JWT signature, issuer, audience and expiry through JWKS.
- **Why:** Managed OIDC avoids storing passwords while providing a standards-based browser login and API security boundary.
- **Rejected:** Self-hosted passwords and magic-link email delivery for the MVP.
- **Open:** Auth0 tenant values remain environment configuration and must be exercised with a test tenant.

### D-024 — Docker Compose runtime
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Run PostgreSQL with pgvector, FastAPI, the scheduled worker and the React frontend through Docker Compose.
- **Why:** One reproducible runtime keeps local setup and service dependencies explicit without committing to a cloud platform.
- **Rejected:** Uncoordinated local processes and MVP cloud infrastructure.
- **Open:** Production hosting is deferred.

### D-025 — Gold corpus plus scheduled polling
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Lock and load the verified gold corpus first, then poll RBI drafts, notifications, Master Directions and withdrawn-circular listings on the planned schedule.
- **Why:** The gold set provides deterministic acceptance data, while limited polling proves idempotent live discovery without crawling the full RBI site.
- **Rejected:** A fixed corpus with no live discovery and broad RBI crawling.
- **Open:** Use an RBI RSS feed only if Phase 0 verifies an official working URL; listing-page polling is the default.

### D-026 — Gemini as the first LLM provider
- **Date:** 2026-11-01 · **Status:** Accepted; supersedes the provider choice in D-016
- **Decision:** Implement Google Gemini as the first hosted LLM adapter while preserving the provider-neutral `llm.complete(input, schema)` application interface.
- **Why:** The selected provider is Gemini, but domain logic must not depend on its SDK or wire format.
- **Rejected:** OpenAI as the first adapter and provider-specific calls inside extraction, retrieval or answer modules.
- **Open:** Additional providers are outside the MVP.

### D-027 — Gemini Interactions API with structured output
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Use `google-genai`, the Gemini Interactions API, `gemini-3.8-flash`, `store=false`, Pydantic-generated JSON Schema and local Pydantic validation. Configure it with `GEMINI_API_KEY`, `GEMINI_EXTRACT_MODEL=gemini-3.8-flash`, and `GEMINI_ANSWER_MODEL=gemini-3.8-flash`.
- **Why:** Google recommends the Interactions API for new integrations and lists Gemini 3.8 Flash as stable. Local validation is still required because structured decoding supports only part of JSON Schema and does not establish factual correctness.
- **Rejected:** The legacy `generateContent` API, unstructured text parsing and server-stored conversations.
- **Open:** Model identifiers remain environment-configurable and must be checked against official Google documentation before upgrades.

### D-028 — Deterministic evidence remains authoritative
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Gemini may propose extraction candidates and answer claims, but it cannot create a `VERIFIED` relationship or bypass deterministic quote and source-location validation. Gemini search grounding and URL Context are disabled.
- **Why:** A schema-valid model response can still be factually wrong; regulatory evidence must come only from the ingested official corpus.
- **Rejected:** Model-decided legal relationships and externally grounded regulatory answers.
- **Open:** None.

### D-029 — Authenticated ownership enforcement
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Map the verified Auth0 `sub` claim to an internal user record and scope every profile, cached analysis and question query by that internal ID. Never accept the effective user ID from browser input.
- **Why:** This prevents horizontal access caused by trusting a client-supplied identifier.
- **Rejected:** Anonymous shared profiles and client-selected ownership.
- **Open:** Acceptance requires explicit cross-user API tests.

### D-030 — Immutable document versions
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** A changed source hash creates a new immutable `document_versions` row, and clauses belong to a specific version.
- **Why:** Amendment diffs, lifecycle decisions and citations must remain reproducible after RBI updates a page or PDF.
- **Rejected:** Overwriting document text or attaching every clause directly to a mutable document row.
- **Open:** Retention of raw cached files will be revisited only if storage becomes material.

### D-031 — Source-specific evidence locations
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** PDF evidence stores a page; HTML evidence stores a DOM locator; both store normalized-text character offsets, the source URL and the verbatim evidence text.
- **Why:** An HTML-first parser cannot truthfully provide PDF page numbers, while every verified claim still needs a reproducible source location.
- **Rejected:** Requiring a page for HTML and storing quotes without offsets.
- **Open:** DOM locator stability is validated against the gold corpus in Phase 1.

### D-032 — Corrected lifecycle representation
- **Date:** 2026-11-01 · **Status:** Accepted; supersedes the state representation in D-005
- **Decision:** Store effective lifecycle state as `DRAFT`, `IN_FORCE`, `REPEALED` or `SUPERSEDED`. Keep `AMENDS`, `REPLACES`, `REPEALS` and `CONSOLIDATED_INTO` as relationships and derive display labels from state plus verified edges.
- **Why:** A document can be in force and amended simultaneously, so amendment and consolidation are not mutually exclusive legal states.
- **Rejected:** A single enum mixing effective state with relationship history.
- **Open:** Lifecycle rules must be validated against the microfinance consolidation chain.

### D-033 — Separate embedding storage
- **Date:** 2026-11-01 · **Status:** Accepted; reaffirms D-019 without ownership semantics
- **Decision:** Keep BGE-M3 as the MVP embedding model and store vectors only in `clause_embeddings`, keyed by clause and model.
- **Why:** Separate storage allows embeddings to be rebuilt or compared without mutating source clauses.
- **Rejected:** Embedding columns on `clauses` and Gemini-generated embeddings in the MVP.
- **Open:** The planned recall@5 evaluation may supersede BGE-M3 later.

### D-034 — Single-workstream implementation
- **Date:** 2026-11-01 · **Status:** Accepted; supersedes the workflow in D-020
- **Decision:** Do not use role-specific ownership or workflow rules. Preserve pull-based, idempotent reconciliation from D-021 as an architectural boundary.
- **Why:** The current build is one coordinated workstream, but decoupled jobs still improve rerun safety and failure isolation.
- **Rejected:** Role-owned tables, role-specific decision ranges and cross-module calls from ingestion.
- **Open:** None.

### D-035 — Official RBI sources only
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Store regulatory evidence only from official RBI pages or files. Search engines and third-party mirrors may help discover an official URL but cannot supply authoritative corpus text.
- **Why:** Evidence must be independently traceable to the regulator and protected from mirror edits or incomplete copies.
- **Rejected:** Treating aggregators, search snippets or model knowledge as regulatory evidence.
- **Open:** Every gold record must receive an official URL and content hash in Phase 0.

---

### D-036 — Normalized regulatory text defines a document version
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Use SHA-256 of normalized document-body text as `document_versions.content_hash`; retain separately cached raw responses using their raw-byte hash.
- **Why:** RBI pages contain dynamic navigation markup and presentation changes that vary between requests without changing regulatory text. Raw-byte hashes created false versions during the Phase 1 live run.
- **Rejected:** Raw HTML bytes as version identity and dropping the raw cache.
- **Open:** Conditional HTTP requests remain a later fetch optimization; content idempotency is already enforced.

### D-037 — Source order is the clause occurrence identity
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Store a positive `ordinal` unique within each document version. Keep `path` as a regulatory label but do not require it to be unique.
- **Why:** RBI pages can contain a covering letter and an enclosed direction with repeated paragraph numbers, and annexes can reuse numbering. Rejecting repeated paths lost valid source text.
- **Rejected:** A unique `(document_version_id, path)` constraint and invented suffixes in official clause labels.
- **Open:** Annex-aware semantic paths can be added without changing source ordinals.

### D-038 — Compose database binds to host port 5433
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Bind the PostgreSQL container to `${POSTGRES_PORT:-5433}` on the host while retaining port 5432 inside the Compose network.
- **Why:** The development machine already uses host port 5432; the alternate default avoids interfering with that database.
- **Rejected:** Stopping or replacing the existing PostgreSQL instance.
- **Open:** Deployments may override `POSTGRES_PORT`.

### D-039 — Gold sources require identifier validation
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Before persistence, require every configured RBI and departmental reference to appear in the normalized official source after whitespace normalization.
- **Why:** RBI numeric page IDs are adjacent and opaque. Clause checks alone initially accepted the Universal Banks Licensing page for the MFI manifest entry; identifier validation caught and blocked that mismatch.
- **Rejected:** Trusting a URL because its page ID was inferred or because it contains expected clause numbers.
- **Open:** Title validation may be added as a second signal, but identifiers are mandatory.

---

### D-040 — Live discovery is title-keyword filtered and endpoint allowlisted
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Poll the four official RBI listing pages, match configurable case-insensitive title keywords, accept only known RBI detail endpoints, assign stable URL-derived source keys, and cap each source at `RBI_DISCOVERY_MAX_MATCHES_PER_SOURCE` matches per run.
- **Why:** RBI listing pages include decades of archives and navigation links. An endpoint allowlist prevents off-site or non-document ingestion, while a cap keeps the MVP within its small-catalogue scope. A live KYC draft was discovered from the official draft listing and its immediate rerun created zero versions.
- **Rejected:** Site-wide crawling, unbounded archive ingestion, accepting arbitrary same-page links, and semantic/LLM discovery.
- **Open:** Topic ontology and full-text matching can supplement title keywords after deterministic evaluation; they must not broaden evidence beyond official RBI sources.

### D-041 — APScheduler owns periodic listing polls
- **Date:** 2026-11-01 · **Status:** Accepted
- **Decision:** Use APScheduler 3 in the dedicated Compose worker. Poll drafts and notifications every three hours on weekdays, staggered by 20 minutes; poll Master Directions and withdrawn circulars daily at 01:00 and 02:00 in `RBI_SCHEDULER_TIMEZONE`. Bootstrap the gold corpus before starting the scheduler, with optional immediate live polling controlled by `RBI_SCHEDULER_RUN_ON_STARTUP`.
- **Why:** A separate asyncio scheduler keeps polling out of API requests, meets the minimum three-hour cadence, prevents overlapping instances, and preserves one audited `ingest_runs` row per source execution. The built worker remained running after a successful gold bootstrap.
- **Rejected:** FastAPI background tasks, polling faster than three hours, one broad crawl job, and requiring immediate live archive scans on every container restart.
- **Open:** Production deployment may add persistent scheduler state if more than one worker replica is introduced; the MVP runs exactly one worker.

---

## Template for new entries

```
### D-0xx — Title
- **Date:** YYYY-MM-DD · **Status:** Accepted | Provisional | Superseded by D-0yy
- **Decision:** What was decided.
- **Why:** The reason, including constraints and evidence.
- **Rejected:** Alternatives considered (optional).
- **Open:** What would change this decision (optional).
```
