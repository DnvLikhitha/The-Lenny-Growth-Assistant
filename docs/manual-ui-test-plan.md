# Manual UI Test Plan — The Lenny Growth Assistant

This manual test plan covers the key end-to-end user flows defined in `PRD.md §2.1`.

---

## 1. Flow A — Grounded Q&A

- [ ] **Step 1: Start New Session**
  - Click `+ New Session` in the left session rail.
  - Verify a new session card appears and opens.

- [ ] **Step 2: Submit Grounded Question**
  - Type: `"How should top PMs think about user activation in PLG products?"`
  - Click `Send` or press `Enter`.
  - Verify status indicator displays `🔍 Retrieving transcript context...` followed by `⚡ Generating grounded response...`.

- [ ] **Step 3: Verify Citations & Grounding**
  - Verify assistant message contains transcript citations (chips showing guest name, episode title, and timestamp).
  - Click a citation chip and verify source path metadata is shown.

- [ ] **Step 4: Verify Low Grounding Refusal**
  - Type an out-of-domain query: `"What is the best recipe for baking sourdough bread?"`
  - Verify assistant refuses to fabricate and states insufficient grounding in Lenny's transcripts.

---

## 2. Flow B — Ship 30 for 30 Essay Generation

- [ ] **Step 1: Request Essay**
  - Type topic: `"Key lessons on pricing and packaging PLG products"`
  - Click `Ship 30 Essay` button.
  - Verify status changes to `📝 Writing Ship 30 essay artifact...`.

- [ ] **Step 2: Verify Artifact Viewer**
  - Verify Artifact Viewer panel opens on the right zone.
  - Verify Word Count and `Structure Valid: ✅ PASS` are displayed.
  - Toggle between `View Raw` and `View Rendered`.

---

## 3. Flow C — Model & Provider Resilience

- [ ] **Step 1: Check Provider Indicator**
  - Look at top-right header badge displaying `Provider: ollama (llama3.1:8b)`.

- [ ] **Step 2: Missing API Key / Unreachable Provider Error**
  - Set `LLM_PROVIDER=anthropic` without providing `ANTHROPIC_API_KEY`.
  - Submit a message and verify a structured, user-friendly error banner appears rather than a crash or unhandled exception.
