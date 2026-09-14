# PRD — The Lenny Growth Assistant

**Status:** Draft v1
**Owner:** Forward Deployed Engineer (take-home submission)
**Related docs:** [`design.md`](./design.md) · [`architecture.md`](./architecture.md) · [`README.md`](../README.md)

---

## 1. Forward Deployment Brief

### 1.1 User and problem

**Primary user:** An internal operator at a product/growth org — a PM, growth marketer, or founder — who wants fast, trustworthy answers to product and growth questions without reading or searching through hundreds of hours of podcast transcripts.

**Secondary user:** The same person acting as a *content creator*, who wants to turn an insight they just learned into a publishable essay or shareable artifact without opening a separate writing tool.

**Job to be done:** "When I have a product/growth question (e.g. 'how should we think about activation for a PLG product?'), I want a grounded, cited answer pulled from real operator conversations — and if the answer is good, I want to turn it into something I can publish — without hunting through transcripts or prompting an LLM from scratch."

**Pain removed:**
- Replaces manual search across 269+ long-form transcripts with a single conversational interface.
- Removes the risk of "confidently wrong" AI answers by grounding every response in a traceable source.
- Removes the friction of going from *insight* → *polished written artifact* (today this means copy-pasting into a separate doc/writing tool and manually reformatting).

### 1.2 Success metric

Primary (product): **≥90% of answered questions include at least one correctly attributed transcript citation**, measured against a manual eval set of ~25 representative PM/growth questions run against the local (Ollama) and cloud model paths.

Secondary (operational): **Time-to-first-grounded-answer ≤ 15s (cloud) / ≤ 45s (local Ollama, 7–8B class model)** on a standard dev laptop, since latency is the main adoption blocker for a local-first internal tool.

Tertiary (content): **Ship 30 for 30 artifact meets its own spec** (≈1,250 words ±15%, includes hook + headings + bold emphasis + a stated takeaway) on ≥90% of generation attempts, checked by an automated word-count/structure assertion in tests, not just eyeballing.

These are the metrics this submission is actually instrumented and tested against; a production rollout would add engagement metrics (session return rate, artifacts published) that require real usage data this take-home can't generate.

### 1.3 Assumptions

The brief is intentionally open-ended, so the following assumptions were made explicit and are treated as the contract for this build:

1. **Corpus:** The `ChatPRD/lennys-podcast-transcripts` repo (269 Markdown transcripts under `episodes/<slug>/transcript.md`, plus a topic `index/` and per-episode metadata) is the sole knowledge source. No live scraping of new episodes is in scope.
2. **Users are internal/trusted**, not end customers — so this build prioritizes correctness and traceability over multi-tenant auth, rate limiting, or fine-grained permissions. A single `users` concept is enough to demonstrate the persistence model; full auth (SSO, RBAC) is out of scope.
3. **"Complex product and growth questions"** means synthesis across episodes (e.g. "what do multiple guests say about pricing PLG products?"), not just single-document lookup — this is the reason retrieval must support **multi-chunk, multi-episode** context, not a single top-1 match.
4. **Local model quality is understood to be weaker than cloud.** The brief mandates Ollama for the demo; this PRD assumes the evaluator accepts a documented quality gap for local models rather than expecting cloud-parity from a 7–8B local model.
5. **"Deploy locally"** means a fully reproducible `docker compose up` on the evaluator's machine, not a hosted URL — Supabase/Railway are used as managed Postgres, not as a public hosting target for the whole app.
6. **Cost and rate limits are a demo-scale concern.** No budget/usage caps are enforced beyond basic timeout/retry handling; this is flagged as a risk, not solved.

### 1.4 Scope choices

**In scope**
- Conversational RAG assistant over the full transcript corpus, with session-scoped memory and citations.
- Ship 30 for 30 essay-generation skill, implemented as a distinct, structured skill (its own prompt template + validation), not an ad hoc instruction.
- Markdown/HTML artifact generation with an in-app, sandboxed Artifact Viewer.
- Cloud (Anthropic Claude) + local (Ollama) model backends behind a single provider interface, switchable via config/UI, with graceful fallback.
- FastAPI backend, Postgres persistence (sessions, messages, metadata), Docker Compose deployment.
- Automated tests for retrieval, routing, persistence, and API contracts; a manual UI test plan.

**Explicitly out of scope**
- Multi-user auth/RBAC, billing, or multi-tenant isolation.
- Ingesting anything beyond the provided transcript repo (no live YouTube/RSS scraping).
- Fine-tuning any model — this is a prompting + retrieval system, not a training exercise.
- Streaming voice, mobile app, or non-English support.
- Production-grade autoscaling/CDN — Compose is sufficient for the stated deployment bar.
- A general-purpose artifact type system — only Markdown and self-contained HTML/CSS are supported artifact kinds (matches §4.3 of the brief).

### 1.5 Risks and trade-offs

| Risk | Impact | Mitigation in this build |
|---|---|---|
| **Hallucination** — model answers beyond what transcripts support | Erodes trust, the core value prop | Retrieval-grounded system prompt that requires citing source episodes; explicit "not enough information" fallback path when retrieval score is below threshold; eval set to catch regressions |
| **Local model quality** — Ollama model may under-perform on synthesis-heavy questions | Demo looks worse than the cloud path | Document the gap explicitly in README; keep the same RAG context regardless of backend so the *retrieval* quality doesn't degrade, only generation quality |
| **Latency** — RAG + local inference can be slow | Poor perceived UX | Stream tokens to the UI, show retrieval progress state, cap context to top-k chunks instead of long-context stuffing |
| **Cost (cloud)** | Runaway spend in shared eval environments | Config-level max-token caps, no automatic retries-with-backoff loops beyond a small bounded number |
| **Data leakage** — Transcript content or user queries logged insecurely | Structured logs redact message bodies at INFO level by default; secrets never logged; `.env` never committed |
| **Unsafe artifact rendering** — Generated HTML could carry XSS if rendered unsanitized | Artifacts render in a sandboxed `iframe` (`sandbox="allow-same-origin"` only, no `allow-scripts` for HTML artifacts) — detailed in `architecture.md` §Security |
| **Retrieval staleness/traceability** — Answers cite the wrong or a stale chunk | Every chunk stores its source file path + episode slug + approximate timestamp anchor so citations are checkable against the repo |

---

## 2. Product requirements

### 2.1 User flows

**Flow A — Grounded Q&A**
1. User opens the app → lands in a new session (or resumes a listed prior session).
2. User asks a product/growth question.
3. System retrieves relevant transcript chunks, generates an answer with inline citations (episode + guest name), and displays retrieval sources alongside the answer.
4. User asks a follow-up; prior turns remain in context for that session.
5. If retrieval confidence is low, the assistant states it can't find sufficient grounding rather than guessing.

**Flow B — Ship 30 for 30 essay**
1. From an existing grounded conversation (or a fresh topic prompt), user invokes the "write a Ship 30 for 30 essay" action.
2. Skill re-queries the knowledge base for supporting material on the topic, applies the encoded Ship 30 for 30 structure/style rules, and generates the essay as a Markdown artifact.
3. Artifact opens in the Artifact Viewer beside the chat; word count and structural checks are shown (or flagged if out of spec).

**Flow C — Artifact generation (general)**
1. User asks for a Markdown doc or an HTML/CSS snippet based on the conversation so far.
2. Assistant returns the artifact; Artifact Viewer renders it in an isolated frame with a toggle between rendered view and raw source.
3. User can copy/download the artifact.

**Flow D — Model configuration**
1. Evaluator sets `LLM_PROVIDER=anthropic|ollama` (and model name) via `.env` or a UI selector.
2. Active provider is visibly shown in the chat header.
3. If the selected provider is unavailable (no API key / Ollama not running), the system surfaces a clear, actionable error rather than failing silently or hanging.

### 2.2 Acceptance criteria

- [ ] A new chat session can be started and persists independently of other sessions in Postgres (verified by reopening a session and seeing prior turns).
- [ ] A follow-up question correctly uses prior turn context within the same session.
- [ ] At least 90% of grounded answers in the eval set include a correct, checkable citation to a transcript file.
- [ ] Asking a question with no relevant transcript coverage produces an explicit "insufficient grounding" response, not a fabricated answer.
- [ ] The Ship 30 for 30 skill produces an artifact within the specified word range and includes headings, bold emphasis, and a stated takeaway.
- [ ] A generated HTML artifact cannot execute a script that accesses the parent page (verified by a test artifact containing a script tag).
- [ ] Switching `LLM_PROVIDER` between Ollama and Anthropic changes generation behavior without any code change, and the active provider is visible in the UI.
- [ ] `docker compose up` on a clean machine (with `.env` populated from `.env.example`) brings up API, DB, and frontend without manual steps beyond documented ones.
- [ ] Killing Ollama mid-session produces a graceful, user-visible error rather than a hang or crash.
- [ ] Automated tests pass for: API contract validation, retrieval relevance on a fixed query set, session persistence, and provider routing.

### 2.3 Implementation plan

1. **Ingestion pipeline** — clone/sync transcript repo, parse per-episode Markdown + metadata, chunk (semantic/paragraph-based, with episode/timestamp provenance), embed, store in Postgres (pgvector) or a lightweight vector index.
2. **Retrieval + grounding** — top-k similarity search, source-attributed context assembly, "insufficient grounding" threshold logic.
3. **Agent layer** — Claude Agent SDK–based orchestration: a Q&A tool/skill and a distinct Ship 30 for 30 skill, both consuming the same retrieval tool.
4. **Model provider abstraction** — common interface over Anthropic and Ollama; config-driven selection; timeout/fallback handling.
5. **API layer (FastAPI)** — session endpoints, chat endpoint (streaming), artifact endpoint, health/readiness endpoints, structured error responses.
6. **Persistence (Postgres)** — sessions, messages, artifacts, retrieval-trace metadata.
7. **Frontend** — chat UI, session list, model indicator, Artifact Viewer (sandboxed rendering pane).
8. **Deployment & ops** — Docker Compose, `.env.example`, structured logging, resilience handling for the failure modes in §1.5.
9. **Tests & docs** — automated tests per acceptance criteria, manual UI test plan, README/architecture/design docs, demo video.

Given the compressed timeline, steps 1–5 (the grounded Q&A core) are the priority path; the Ship 30 skill, artifact viewer polish, and full ops hardening follow once the core loop is demonstrably working end-to-end.
