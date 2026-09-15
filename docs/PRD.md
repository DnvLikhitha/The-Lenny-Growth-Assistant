# PRD — The Lenny Growth Assistant

**Status:** Final v1.0
**Owner:** Forward Deployed Engineer Submission
**Related docs:** [`design.md`](./design.md) · [`architecture.md`](./architecture.md) · [`README.md`](../README.md)

---

## 1. Forward Deployment Brief

### 1.1 User and Problem

**Primary user:** An internal operator at a product/growth organization (PM, growth marketer, or founder) seeking rapid, trustworthy answers to product and growth questions grounded strictly in Lenny's Podcast transcripts without searching through hundreds of hours of recordings.

**Secondary user:** A content creator or growth practitioner who wants to turn insights into publishable, structured essays (Ship 30 for 30 framework) or rendered HTML/Markdown artifacts without leaving the workspace.

**Job to be done:** "When I have a product/growth question (e.g., 'How should top PMs think about user activation in PLG products?'), I want a grounded, cited answer pulled from real operator conversations with clickable source citations — and if the answer is good, I want to generate a structured essay artifact I can publish."

**Pain removed:**
- Replaces manual search across 260+ long-form transcripts with a single conversational vector RAG interface.
- Eliminates "confidently wrong" AI hallucinations by enforcing strict grounding score thresholds and source attribution.
- Eliminates friction when converting insights into polished written artifacts.

---

### 1.2 Success Metrics

- **Grounding Accuracy:** ≥90% of answered queries contain valid, checkable citations to guest transcript chunks.
- **Latency:** Time-to-first-token ≤ 10s (cloud Claude) / ≤ 25s (local Ollama 3B model on standard laptop CPU).
- **Artifact Quality:** 100% of Ship 30 essays pass automated server-side structural checks (hook, headings, bold emphasis, and key takeaway section).
- **Security:** 0 execution vulnerabilities on untrusted HTML/Markdown artifacts (enforced via `sandbox="allow-same-origin"` and sanitization).

---

### 1.3 Corpus & Scope Boundaries

- **Knowledge Source:** `ChatPRD/lennys-podcast-transcripts` (260+ markdown transcript files).
- **In Scope:** Vector RAG retrieval, session management, inline session rename & delete, swappable local (Ollama) / cloud (Anthropic) model provider, Ship 30 essay generation skill, sandboxed artifact viewer, Docker Compose deployment, automated pytest suite.
- **Out of Scope:** Multi-tenant auth/SSO, live YouTube scraping, model fine-tuning.

---

## 2. Product Requirements & Key User Flows

### 2.1 User Flows

#### Flow A — Grounded Q&A
1. User lands on the workspace (`http://localhost:3000` or `:3001`).
2. User submits a product/growth query or clicks a suggested prompt card (*User Activation Levers, SaaS Pricing, Product-Market Fit, Early PM Hiring*).
3. The system executes vector similarity search against 260+ transcript chunks.
4. If aggregate relevance score ≥ `0.38`, assistant streams a cited answer with clickable source chips (`📍 Guest — Episode Title (00:12:34)`).
5. If aggregate relevance score < `0.38`, assistant returns an explicit refusal stating insufficient grounding.

#### Flow B — Ship 30 for 30 Essay Skill
1. User enters a topic and clicks **Ship 30 Essay**.
2. System retrieves relevant transcript chunks and formats a structured essay (~1,250 words / ≥400 words for local models) with a hook, `##` headers, bold bullet points, and a **Key Takeaway** section.
3. Server-side validator runs `validate_ship30_essay()` and stores `structure_valid` status.
4. The Artifact Viewer opens on the right zone displaying word count, structure status (`✅ PASS`), and rendering controls.

#### Flow C — Session Management
1. User creates new sessions via **+ New Chat Session**.
2. User renames any session inline using the `✏️` pencil icon.
3. User deletes unwanted sessions and their associated history using the `🗑️` trash icon.

---

## 3. Acceptance Criteria

- [x] Full transcript dataset chunked and indexed in PostgreSQL with `pgvector`.
- [x] Swappable provider abstraction (Ollama default, Anthropic cloud) configurable via `LLM_PROVIDER` and `LLM_MODEL`.
- [x] Strict grounding threshold (`GROUNDING_THRESHOLD = 0.38`) preventing hallucination on out-of-domain queries.
- [x] Ship 30 essay skill with automated server-side structural validator.
- [x] HTML/Markdown artifact rendering strictly sandboxed with `sandbox="allow-same-origin"` ONLY.
- [x] Modern Light Theme React UI matching SaaS design standards.
- [x] Inline session renaming and session deletion in frontend sidebar.
- [x] One-command Docker Compose deployment (`docker compose up -d`).
- [x] Complete automated test suite (18 passing pytest cases).
