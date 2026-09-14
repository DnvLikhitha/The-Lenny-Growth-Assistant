# The Lenny Growth Assistant

An AI-powered conversational web application grounded in Lenny's Podcast transcripts. Built with FastAPI, PostgreSQL + pgvector, React, Ollama (local LLM), and Anthropic Claude (cloud LLM).

---

## 🚀 Quick Start (One-Command Docker Compose)

```bash
docker compose up -d
```

Access the web UI at `http://localhost:3000` and API docs at `http://localhost:8000/docs`.

### 🦙 Ollama Model Pull (Local Demo)

When running locally with Ollama, pull the default `llama3.1:8b` model:

```bash
docker exec -it lenny_ollama ollama pull llama3.1:8b
```

---

## 🛠️ Prerequisites

- **Docker & Docker Compose**
- **Python 3.11+** (for local development outside Docker)
- **Node.js 18+** (for frontend development outside Docker)

---

## ⚙️ Environment Variables

Copy `backend/.env.example` to `backend/.env` or configure variables in your environment:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5435/lenny_assistant` | PostgreSQL + pgvector connection string |
| `LLM_PROVIDER` | `ollama` | Active provider (`ollama` or `anthropic`) |
| `LLM_MODEL` | `llama3.1:8b` | Model name for provider |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama service URL |
| `ANTHROPIC_API_KEY` | *(optional)* | Required only when `LLM_PROVIDER=anthropic` |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | SentenceTransformer embedding model name |

---

## 🧪 Running Automated Tests

Run the full pytest suite covering ingestion, retrieval, provider routing, FastAPI REST/SSE endpoints, artifact sandboxing, and logging:

```bash
python -m pytest -v
```

---

## 📜 Manual UI Test Plan

See [`docs/manual-ui-test-plan.md`](docs/manual-ui-test-plan.md) for step-by-step verification instructions.
