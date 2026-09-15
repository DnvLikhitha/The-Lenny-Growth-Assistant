# Design System & UI/UX Specification — The Lenny Growth Assistant

**Status:** Final v1.0
**Theme:** Modern Professional SaaS Light Theme
**Related docs:** [`PRD.md`](./PRD.md) · [`architecture.md`](./architecture.md) · [`README.md`](../README.md)

---

## 1. Visual Hierarchy & Color Palette

The interface follows a clean, professional SaaS light theme palette designed for clarity, high contrast, and readability:

| Variable | Value | Role |
|---|---|---|
| `--bg-main` | `#f8fafc` | Primary canvas background (Slate 50) |
| `--bg-sidebar` | `#ffffff` | Session rail & Artifact viewer background |
| `--bg-card` | `#ffffff` | Assistant message containers & suggested prompt cards |
| `--bg-user-msg` | `#2563eb` | User chat bubble fill (Blue 600) |
| `--text-primary` | `#0f172a` | Primary headings and body text (Slate 900) |
| `--text-secondary` | `#475569` | Secondary subtitles and metadata (Slate 600) |
| `--text-muted` | `#64748b` | Timestamps and labels (Slate 500) |
| `--accent-primary` | `#2563eb` | Primary buttons and highlights |
| `--accent-secondary` | `#059669` | Emerald green for **Ship 30 Essay** action |
| `--border-subtle` | `#e2e8f0` | Card borders and divider lines (Slate 200) |

---

## 2. Three-Zone Layout Architecture

The application implements a responsive 3-zone layout:

```text
+----------------------+---------------------------------------+-----------------------+
|  SESSION RAIL        |  CONVERSATIONAL WORKSPACE             |  ARTIFACT VIEWER      |
|  (280px)             |  (Flexible)                           |  (480px)              |
|                      |                                       |                       |
|  [L] Lenny Growth    |  [Header: Provider & Live Status]     |  [Artifact Header]    |
|  + New Chat Session  |                                       |                       |
|                      |  [Chat Messages / Welcome Cards]      |  Word Count: 1,210    |
|  CHAT HISTORY        |                                       |  Structure: ✅ PASS   |
|  - PLG Onboarding ✏️🗑️|  - User Query Bubble                  |                       |
|  - PM Hiring ✏️🗑️    |  - Grounded Assistant Bubble          |  [Sandboxed Iframe /  |
|                      |    📍 Citation Chips                  |   Rendered Markdown]  |
|                      |                                       |                       |
|                      |  [Input Bar: Send | Ship 30 Essay]    |                       |
+----------------------+---------------------------------------+-----------------------+
```

### Zone 1: Session Rail (Left Sidebar — 280px)
- **Branding:** Logo icon (`L`) with application title and subtitle.
- **Primary Action:** `+ New Chat Session` button.
- **Chat History List:** Chronological list of user sessions with active selection highlighting (`#eff6ff`).
- **Interactive Actions on Hover:**
  - **Inline Rename (✏️):** Converts title into an inline input box. Pressing `Enter` commits `PATCH /sessions/{id}`.
  - **Delete Session (🗑️):** Sends `DELETE /sessions/{id}` and updates sidebar instantly.

### Zone 2: Conversational Workspace (Center)
- **Header:** Title + Provider badge showing active backend (`ollama (llama3.2:3b)` or `anthropic`) with a green status dot.
- **Welcome / Empty State:** Displays a welcome hero header with 4 interactive suggested prompt cards (*User Activation Levers, SaaS Pricing, Product-Market Fit, Early PM Hiring*).
- **Message Bubbles:**
  - User messages aligned right in solid blue (`#2563eb`).
  - Assistant messages aligned left in elevated white cards with subtle borders (`#e2e8f0`).
  - Clickable citation chips (`📍 Guest — Episode Title (00:12:34)`) listed under grounded answers.
- **Input Controls:** Bottom input container with dual actions:
  - **Send:** Triggers grounded Q&A stream (`answer_question`).
  - **Ship 30 Essay:** Triggers Ship 30 essay generation skill (`write_ship30_essay`).

### Zone 3: Artifact Viewer (Right Panel — 480px)
- Opens dynamically when a Ship 30 essay or document artifact is created.
- **Header Badge:** Displays total word count and automated structure status (`Structure: ✅ PASS`).
- **View Toggle:** Switch between `View Rendered` (formatted HTML typography) and `View Raw Source` (monospaced markdown).
- **Security:** HTML artifacts render inside an `iframe` with `sandbox="allow-same-origin"` ONLY.

---

## 3. Interaction States & Transitions

| State | Visual Behavior |
|---|---|
| **Retrieving Context** | Status pill shows: `🔍 Searching 260+ transcript chunks...` |
| **Streaming Tokens** | Tokens stream into assistant bubble via Server-Sent Events (SSE). |
| **Generating Artifact** | Status pill shows: `📝 Writing Ship 30 essay artifact...` |
| **Low Grounding** | Assistant returns explicit refusal stating insufficient transcript coverage. |
| **Error State** | Structured error banner displayed inline without crashing session state. |

---

## 4. Responsiveness

- **Desktop (≥1024px):** Full 3-zone layout visible simultaneously.
- **Tablet (768px–1023px):** Stacked vertical zones with collapsible panels.
- **Mobile (<768px):** Single-column layout with sticky input controls at bottom.
