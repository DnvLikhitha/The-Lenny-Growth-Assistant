# design.md — The Lenny Growth Assistant

**Related docs:** [`PRD.md`](./PRD.md) · [`architecture.md`](./architecture.md)

This document covers the UI/UX principles, information architecture, interaction states, and design rationale for the product. It intentionally does not cover implementation (see `architecture.md`) or product scope (see `PRD.md`).

---

## 1. UX principles

1. **Trust is the product.** Every claim the assistant makes must be visibly traceable to a source. Citations are never an afterthought or a footnote the user has to hunt for — they sit inline, next to the claim they support.
2. **Show your work, don't hide the machine.** Retrieval and generation both take visible time, especially on local models. Rather than a spinner that hides what's happening, the UI narrates state ("Searching transcripts…", "Generating with local model (llama3.1:8b)…") so latency reads as *progress*, not a stall.
3. **Never let the assistant bluff.** When retrieval confidence is low, the UI presents a distinct "not enough grounding" state — visually different from a normal answer — instead of a fluent-sounding guess.
4. **The artifact is a first-class object, not a code block.** Generated Markdown/HTML is a document the user will reuse, so it gets its own dedicated, persistent surface (the Artifact Viewer) rather than living only inside a chat bubble.
5. **One system, two model backends, no user confusion.** Whether the answer came from Ollama or Claude, the interaction model is identical. Only a small, persistent indicator differs — the user's mental model of "how do I use this" should never depend on which backend is active.

## 2. Information architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Top bar: app name · session title · active model indicator      │
├───────────────┬─────────────────────────────┬────────────────────┤
│  Session list  │        Chat pane            │   Artifact Viewer  │
│  (left rail)   │  (messages + input + state) │   (right pane,     │
│                │                              │   appears on       │
│  - New chat    │                              │   demand)          │
│  - Session 1   │                              │                    │
│  - Session 2…  │                              │  [Rendered | Raw]  │
└───────────────┴─────────────────────────────┴────────────────────┘
```

**Three-zone layout:**
- **Session rail (left):** list of past sessions with timestamps and an auto-generated title (first question, truncated); "New chat" always visible at top.
- **Chat pane (center):** the primary work surface — message thread, composer, inline citations, state banners.
- **Artifact Viewer (right):** collapsed/hidden until an artifact exists for the session; once generated, persists for the life of the session and is reachable again without regenerating.

This mirrors the Claude Artifacts mental model deliberately, since the brief asks for a "similar to Claude Artifacts" experience and evaluators will already have that reference point.

## 3. Key interaction states

| State | Trigger | UI treatment |
|---|---|---|
| **Empty session** | New chat with no messages | Centered prompt suggestions drawn from common PM/growth topics in the corpus (e.g. "How do top PMs think about activation?") |
| **Retrieving** | Query submitted, before generation starts | Inline status line in the message thread: "Searching Lenny's transcripts…" |
| **Streaming answer** | Model is generating | Tokens stream in; citation chips resolve in as sources are confirmed, not blocked behind full completion |
| **Grounded answer (normal)** | Answer completed with sources above threshold | Answer text + a "Sources" row of chips (episode title + guest), each opens the source excerpt in a side popover |
| **Low-grounding answer** | Retrieval score below threshold | Distinct amber-toned banner: "I couldn't find strong support for this in the transcripts — here's my best partial answer" (or a flat decline, per PRD §2.2) — never styled identically to a confident answer |
| **Artifact generating** | User requests essay/artifact | Artifact Viewer pane opens automatically with a generation-in-progress state; chat shows a compact "Generating artifact…" reference card instead of dumping raw content into the thread |
| **Artifact ready** | Generation complete | Viewer shows rendered output by default with a Raw/Rendered toggle, copy button, and download button; Ship 30 essays additionally show a small compliance strip (word count, structure checklist) |
| **Provider error** | Selected model unavailable (no key / Ollama down) | Non-blocking error banner naming the exact cause and the fix ("Ollama isn't reachable at localhost:11434 — is it running?"), chat input stays usable to retry |
| **DB/session error** | Persistence failure | Session continues in-memory for the current turn with a visible "not saved" warning, rather than losing the user's in-progress question |

## 4. Responsive behavior

- **Desktop (≥1024px):** full three-zone layout as above, session rail and artifact viewer both visible simultaneously.
- **Tablet (~768–1023px):** session rail collapses to an icon-triggered drawer; chat and artifact viewer remain side-by-side but narrower, with the artifact viewer capped at 40% width.
- **Mobile (<768px):** single-column, tab-based navigation — Chat / Artifact / Sessions become three tabs rather than panes, since a split view isn't usable at that width. Generating an artifact automatically switches the active tab to Artifact so the user doesn't miss it.

## 5. Accessibility

- All state changes (retrieving → streaming → complete → error) are announced via an `aria-live="polite"` region so screen reader users get the same progress narration sighted users see, without being interrupted mid-sentence.
- Citation chips are real focusable buttons (not styled `<span>`s) with accessible names like "Source: Episode — Guest Name", not just an icon.
- Color is never the sole signal: the low-grounding state uses an icon + label in addition to the amber tint; error banners use an icon + explicit text.
- Full keyboard operability: session switching, message composer, citation popovers, and the Rendered/Raw artifact toggle are all reachable and operable via keyboard alone, with visible focus rings (contrast-checked against the app's dark and light themes).
- The Artifact Viewer's sandboxed `iframe` (see `architecture.md` §Security) is given an explicit `title` attribute and is skippable via a "Skip artifact preview" link for screen reader users, since iframe content can otherwise be a navigation trap.
- Minimum contrast ratio of 4.5:1 for body text, verified for both the citation-chip and low-grounding banner color treatments specifically, since those are the states most likely to be added late and skipped in a contrast pass.

## 6. Design decisions and rationale

- **Split pane over modal for artifacts:** a modal would block the chat while reviewing an artifact; a persistent side pane lets the user keep refining the artifact through conversation ("make the hook stronger") while seeing both surfaces.
- **Model indicator in the top bar, not buried in settings:** the brief requires the active provider to be visible; putting it in the persistent chrome (not a settings page) means an evaluator switching `.env` and reloading can confirm the toggle worked in one glance.
- **Citations as inline chips, not endnotes:** endnotes are the natural RAG-demo default but decouple the claim from its source visually. Inline chips keep grounding legible even when a user skims.
- **Distinct visual language for "low grounding":** reusing the normal answer style for uncertain answers is the single most common trust failure in RAG demos — a deliberately different treatment makes the assistant's honesty visible rather than implicit in wording alone.
- **Raw/Rendered toggle on every artifact:** engineers evaluating this submission will want to see the generated Markdown/HTML source, not just trust the render — so raw source is always one click away, never hidden.
