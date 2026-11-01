# codex.md — Instructions for Codex on the RAAY project

> Codex's documented instruction file is `AGENTS.md`. Keep this file as `codex.md` for reference, **and** run `cp codex.md AGENTS.md` at the repo root so Codex loads it automatically.

## 1. Mission
Build RAAY: an evidence-backed RBI Regulatory Relationship Engine. Follow `plan.md` phase by phase. Do not skip ahead. Do not add features outside `plan.md`.

**Always record as you build:** keep `decision.md` (design decisions with reasons), `flow.md` (current architecture flowcharts and build status) and `README.md` (problem, solution, architecture, setup and run steps) up to date during every phase. Full rules are in §10. If two people are working, also follow `team.md` and §10.5.

## 2. Non-negotiable rules
1. **No LLM-decided relationships.** An LLM may propose candidates. Only deterministic code may create a `VERIFIED` edge.
2. `AMENDS`, `REPLACES`, `REPEALS`, `CONSOLIDATED_INTO` require explicit source text (amendment instruction or repeal list). Semantic similarity may only create `CANDIDATE` / `RELATED_TO`.
3. Every `VERIFIED` edge stores: quote, page, `char_start`, `char_end`, source URL, extractor name + version.
4. **Quote-span validator:** any evidence string from an LLM must appear in the source after whitespace/Unicode normalisation. If not, discard it.
5. If a reference cannot be resolved, store `UNRESOLVED`. Never guess a target.
6. Applicability: exclusions override matches. Never output `DIRECT` when an exclusion or unmet condition exists. No numeric "relevance %" anywhere.
7. Lifecycle matters: always expose whether a document is `IN_FORCE`, `AMENDED`, `REPEALED` or `CONSOLIDATED_INTO` something. On 28 Nov 2025 RBI consolidated its instructions into 244 Master Directions and withdrew thousands of circulars, so many "amendments" are now historical.
8. Do not hard-code any RBI reference number from memory. Fetch it from the RBI site and record the URL in `data/gold/corpus.yaml`. The KYC amendment reference in the blueprint is unverified.
9. Be a polite scraper: throttle (≥1 s between requests), cache raw responses on disk, send a descriptive User-Agent, honour robots.txt, never re-download unchanged content (compare SHA-256).

## 3. Tools and plugins

### 3.1 Context7 (required)
Use Context7 whenever you write code against a library API, so you use the current version and not remembered syntax.

Install (pick one):
```bash
codex mcp add context7 -- npx -y @upstash/context7-mcp
# or let the vendor script configure both MCP and AGENTS.md
npx ctx7 setup --codex
```
Equivalent `~/.codex/config.toml` (or project-scoped `.codex/config.toml` in a trusted project):
```toml
[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp"]
startup_timeout_sec = 30   # first npx run can exceed the default 10 s
```
Verify inside Codex with `/mcp`. Start a new Codex thread after installing.

**When to call Context7** (say "use context7" in the query, resolve the library ID first, then fetch docs for the specific topic, and include the version):
- FastAPI: dependency injection, background tasks, lifespan events
- psycopg 3 / SQLAlchemy 2: async pools, `COPY`, JSONB
- pgvector (Python client + SQL): index types, distance operators, hybrid queries
- PyMuPDF: text blocks with coordinates, page rendering
- httpx: async client, retries, timeouts
- selectolax or BeautifulSoup: CSS selectors
- rapidfuzz: scorers (`token_set_ratio`, `WRatio`)
- pydantic v2: validators, `model_validate_json`
- React + Vite + chosen router/query library; Tailwind if used
- pytest, pytest-asyncio, Playwright (if used)

Do not use Context7 for RBI content. RBI facts come only from RBI documents in the corpus.

### 3.2 Optional plugins (only if installed; otherwise skip silently)
| Tool | Use for |
|------|---------|
| Playwright MCP | Smoke-test the Explorer UI in Phase 5/6 (open page, click badge, assert evidence panel text) |
| GitHub MCP | Open PRs / issues per phase, if the repo is on GitHub |
| Postgres access via `psql` | Inspect tables and run EXPLAIN; do not add a DB MCP unless asked |

Rule: prefer the shell for anything the shell can do. Add a plugin only when it removes real work.

## 4. Repo layout (create exactly this)
```
raay/
  AGENTS.md  plan.md  EVAL.md  README.md
  backend/app/{ingest,parse,refs,relations,lifecycle,applicability,retrieval,answer,api}/
  backend/tests/
  db/schema.sql  db/seed_ontology.sql
  data/raw/        # cached downloads (gitignored)
  data/gold/{corpus.yaml,gold_relations.yaml,gold_applicability.yaml}
  contracts/{openapi.yaml,fixtures/}  team.md  decision.md  flow.md  Makefile  CODEOWNERS
  eval/run_eval.py
  frontend/
```

## 5. Workflow for every phase
1. Read the phase in `plan.md` and restate the deliverables as a checklist in your first message.
2. Write **tests first** for the deterministic parts (reference regexes, verb classifier, applicability rules).
3. Implement the smallest thing that passes. Prefer pure functions with typed inputs/outputs.
4. Run `pytest -q` and the phase's acceptance check (below). Fix before moving on.
5. Update the living documents (§10: `decision.md`, `flow.md`, `README.md`), tick the `plan.md` Definition of Done, then commit with message `phaseN: <what>`.
6. If a requirement is ambiguous or the RBI page structure contradicts the plan, **stop and ask** with 2 concrete options.

### Acceptance checks
| Phase | Check |
|-------|-------|
| 0 | `corpus.yaml` has URL, ref, date, hash for all gold docs; ≥10 labelled gold pairs |
| 1 | Re-running ingest creates 0 duplicate rows; every gold clause number is found with page + offsets |
| 2 | RBI/2025-26/44 → MD Microfinance 2022, `AMENDS`, clause `8.1`, `VERIFIED`, with old/new text |
| 3 | Applicability table tests pass, including an `EXCLUDES` case and a subsumption case (NBFC ⊃ NBFC-MFI) |
| 4 | Unsupported question returns "Insufficient evidence"; every claim has clause ID + verified quote |
| 5 | Playwright (or manual) check: clicking a relation badge shows quote, page, official link |
| 6 | `eval/run_eval.py` prints precision, recall, ref-resolution, clause-resolution, evidence coverage |

## 6. Implementation guidance
- **Parsing:** HTML first; PDF only if HTML is missing. Keep page numbers and character offsets for PDFs; keep DOM paths for HTML.
- **Clause tree:** `path` like `8.1.(a).(i)`; store `parent_id`; keep annex text attached to the instruction that introduces it.
- **Reference patterns:** support both `RBI/2025-26/44` and `DoR.FIN.REC.25/03.10.038/2025-26`; store both in `document_aliases`. Handle "Master Direction ... dated <date>", "ibid", "the circular dated".
- **Amendment verbs:** table-driven (amended, substituted, replaced, inserted, deleted, omitted, repealed, withdrawn, superseded). Each pattern has a unit test and a negative test (e.g., "as amended from time to time" must **not** create an AMENDS edge by itself).
- **Resolution order:** exact alias → (title fuzzy ≥ 0.92 AND date match) → else `UNRESOLVED`.
- **Diff:** normalise whitespace and bullet markers, then diff by sentence; store JSON and render in the UI.
- **Retrieval:** staircase order — eligible docs → graph expansion (≤2 hops over VERIFIED edges) → section filter → clause hybrid (FTS + embedding, reciprocal rank fusion). Embeddings only for clauses of selected documents; FTS-only must still work.
- **Answers:** LLM returns JSON `claims[{text, clause_id, quote}]`. Verifier drops any claim whose quote is not in that clause. If nothing survives, return the refusal string.
- **LLM provider:** keep behind one interface (`llm.complete(prompt, schema)`); no provider-specific code outside it. Temperature 0 for extraction.
- **Config:** secrets via env vars only; never commit keys. Provide `.env.example`.

## 6b. Models, config and scheduling (see `plan.md` §1A to §1C)
- Embeddings: default `BAAI/bge-m3` via `sentence-transformers`, 1024-d, local. Model name comes from env `EMBEDDING_MODEL`; store it in `clauses.embedding_model`. Before locking it in, run the 20-query recall@5 test from `plan.md` against Qwen3-Embedding-0.6B and report the numbers.
- LLM access only through `llm.complete(prompt, schema)`. Model names come from env vars (`EXTRACT_MODEL`, `ANSWER_MODEL`), with an Ollama local fallback. Never hard-code a model name in business logic. Check current model IDs in the provider docs (Context7 or official docs) before use.
- Knowledge base is global; only `stakeholder_profiles` and cached results are per user. Never parse documents inside a user request.
- Scheduler: one CLI entry point `python -m app.ingest.run --source drafts|notifications|masterdirs|withdrawn`, idempotent, logging to `ingest_runs`. Poll RBI listing pages; use RSS only if you verified a working feed URL. Do not poll faster than every 3 hours.

## 7. Code standards
Python 3.12, type hints everywhere, `ruff` + `mypy --strict` on `app/`, small modules, no global state, structured logging. SQL in `db/schema.sql` with constraints that enforce the invariants in `plan.md` §2. Frontend: TypeScript, no UI library beyond what is needed.

## 8. Things you must not do
- Do not crawl the entire RBI site; stay within the gold corpus plus a small seeded catalogue.
- Do not invent relationships to make the demo look better.
- Do not report accuracy figures from a tiny set as general accuracy; report counts (e.g., "11/12").
- Do not leave `TODO` in verifier or applicability code.
- Do not modify `data/gold/gold_relations.yaml` to make tests pass; ask first.

## 9. Final report format (after each phase)
```
Phase N done
- Delivered: ...
- Acceptance: pass/fail per check
- Living docs updated: decision.md / flow.md / README.md (list what changed)
- Known gaps: ...
- Next: ...
```

## 10. Living documents (always keep current)
Three files must exist at the repo root and be updated as part of every phase, not at the end. If one is missing, **create it first** (starter copies are provided). A task is not done until these match the code.

### 10.1 `decision.md` — design decision log
- Add an entry whenever you choose between real alternatives: schema or relationship-type changes, library or model choice, matching or retrieval logic, scheduling cadence, scope cuts, or any time you deviate from `plan.md`.
- Entry format: `D-0xx`, date, status (`Accepted` / `Provisional` / `Superseded`), **Decision**, **Why** (constraints, evidence, test results), **Rejected**, **Open**.
- Append only. Never delete or rewrite old entries. To change a decision, add a new entry and mark the old one `Superseded by D-0yy`.
- Record the *reason*, with numbers where you have them (e.g. recall@5 results that picked the embedding model). Also close `Provisional` items when you resolve them.
- If a decision is made after you stop and ask the user, record the user's answer.

### 10.2 `flow.md` — current architecture and build status
- Shows what is **actually built so far**, not just the plan. Keep the Mermaid diagrams accurate to the code.
- At the end of each phase: move components between the `planned`, `wip` and `done` class lines, update the component status table, the "Last updated" and "Current phase" lines, and add a row to the change log that references the related `D-0xx`.
- Mark a component `Done` only when its acceptance check in §5 passes. If the built version differs from the design, mark `Changed`, update the diagram and add a decision entry.
- Validate that every Mermaid block renders (no unquoted parentheses or special characters in labels).

### 10.3 `README.md` — professional project front page
Must always contain, in this order: title and one-line summary; **Problem**; **Solution**; what users can do; **Architecture** (short Mermaid diagram plus link to `flow.md`); tech stack and models; repo layout; **Getting started** (prerequisites, clone/download, environment variables, database setup, ingesting the gold corpus, running backend, frontend, tests, evaluation, scheduler); configuration table; project documents table; current status; limitations and disclaimer.
- Every command in "Getting started" must be one you have actually run on a clean checkout. After each phase, re-run them and fix the README. Never leave commands that do not work.
- State prerequisites with versions (Python, Node, PostgreSQL with `pgvector`, optional Tesseract). List every environment variable in `.env.example` with a one-line description and never put real keys in the repo.
- Use plain, professional language; no marketing claims about accuracy. Quote real numbers from `EVAL.md` only.
- Update "Current status" to match `flow.md`.

### 10.4 Pre-commit checklist
1. `decision.md` has entries for every non-trivial choice made this phase.
2. `flow.md` matches what is built.
3. `README.md` setup works from scratch.
4. `plan.md` Definition of Done is ticked accurately.

### 10.5 Two-person workflow (when `team.md` applies)
- At the start of a session, find out whether you are working as **Person A (Evidence Engine)** or **Person B (Relevance and Product)** from the user's message; if unclear, ask once. Edit only the paths and write only the tables that role owns (`team.md` §3). Shared files (`db/schema.sql`, `contracts/`, `Makefile`, `.env.example`, `CODEOWNERS`) change only through a PR the other person approves, with a `decision.md` entry.
- Dependency is one-way: B reads A's tables; A never imports B's code; B never writes A's tables. Use pull-based jobs, never cross-calls (D-020, D-021).
- Log decisions with your own ID range: Person A `D-A01…`, Person B `D-B01…`. Never renumber or edit the other person's entries.
- `flow.md`: update only your own rows in the status table and your own `class` lines in the diagram (one `class` line per owner per status), to avoid merge conflicts.
- `README.md`: Person A updates ingestion, scheduler and data setup sections; Person B updates API, frontend, models and evaluation sections. Problem, Solution and Architecture change only by PR.
- Develop against `contracts/fixtures/` until the first real snapshot arrives (`make load-snapshot`). If you need something from the other person, propose a contract change (fixture, schema or `openapi.yaml`) instead of waiting.
- Your final phase report must list which living documents you changed and the related decision IDs.
