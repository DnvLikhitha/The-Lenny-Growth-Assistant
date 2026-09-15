# The Lenny Growth Assistant

An AI-powered conversational web application grounded in Lenny's Podcast transcripts. Built with FastAPI, PostgreSQL + pgvector, React, Ollama (local LLM), and Anthropic Claude (cloud LLM).

---

## Table of Contents
- [Overview](#-overview)
- [Architecture & Tech Stack](#-architecture--tech-stack)
- [Key Features](#-key-features)
- [Prerequisites](#-prerequisites)
- [Quick Start for New Users](#-quick-start-for-new-users)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Environment Configuration](#2-environment-configuration)
  - [3. One-Command Launch (Docker Compose)](#3-one-command-launch-docker-compose)
  - [4. Pull Local Ollama LLM](#4-pull-local-ollama-llm)
- [How to Test the Application](#-how-to-test-the-application)
  - [A. Automated Pytest Suite](#a-automated-pytest-suite)
  - [B. Retrieval Evaluation CLI](#b-retrieval-evaluation-cli)
  - [C. Manual UI Test Plan](#c-manual-ui-test-plan)
- [Environment Variables Reference](#-environment-variables-reference)
- [Troubleshooting & FAQs](#-troubleshooting--faqs)

---

## Overview

**The Lenny Growth Assistant** allows product managers, growth marketers, and founders to ask complex product and growth questions and receive answers grounded strictly in **260+ Lenny's Podcast transcripts**. 

Every answer contains clickable, attributed citation chips referencing the guest name, episode title, and approximate timestamp anchor. The assistant also includes a **Ship 30 for 30 Essay Skill** to turn insights into structured, publishable Markdown artifacts.

---

## Architecture & Tech Stack

- **Backend:** FastAPI (Python 3.11) with Uvicorn
- **Vector Database:** PostgreSQL 16 with `pgvector` extension
- **Embeddings:** HuggingFace `SentenceTransformer("all-MiniLM-L6-v2")` (384 dims, dense vector search)
- **Local LLM (Default):** Ollama (`llama3.2:3b` / `llama3.1:8b`)
- **Cloud LLM (Optional):** Anthropic Claude (`claude-3-5-sonnet-20241022`)
- **Frontend:** React 18, Vite, Nginx, Modern Light Theme UI
- **Containerization:** Docker & Docker Compose

---

## Key Features

- **Grounded Vector Search (RAG):** Answers are pulled directly from 260+ transcript markdown files.
- **Anti-Hallucination Guardrails:** Enforces a strict grounding threshold (`GROUNDING_THRESHOLD = 0.38`). Returns an explicit refusal when information is insufficient.
- **Clickable Citations:** Shows source chips (`📍 Guest — Episode Title (00:12:34)`) for every grounded claim.
- **Ship 30 Essay Skill:** Generates 1,250-word structured essays with an automated server-side validator (`validate_ship30_essay`).
- **Sandboxed Artifact Rendering:** Renders HTML/Markdown artifacts in an isolated iframe (`sandbox="allow-same-origin"` ONLY) with strict XSS sanitization.
- **Session Management:** Full session history persistence, inline session renaming, and session deletion.
- **Pluggable Provider Architecture:** Switch between local Ollama and cloud Anthropic via `LLM_PROVIDER` env var without changing backend code.

---

## Prerequisites

Before getting started, ensure you have installed:
- [Git](https://git-scm.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- [Python 3.11+](https://www.python.org/) *(Optional, for local development outside Docker)*
- [Node.js 18+](https://nodejs.org/) *(Optional, for frontend development outside Docker)*

---

## Quick Start for New Users

### 1. Clone the Repository
```bash
git clone https://github.com/DnvLikhitha/The-Lenny-Growth-Assistant.git
cd The-Lenny-Growth-Assistant
```

### 2. Environment Configuration
Copy `.env.example` to create your local `.env` file:
```bash
cp backend/.env.example .env
```

### 3. One-Command Launch (Docker Compose)
Start all containerized services (Frontend, API, PostgreSQL with `pgvector`, and Ollama):
```bash
docker compose up -d
```

Access the application in your browser:
- **Web UI:** [`http://localhost:3000`](http://localhost:3000) *(or `http://localhost:3001` if port 3000 is occupied)*
- **API Documentation:** [`http://localhost:8000/docs`](http://localhost:8000/docs)

### 4. Pull Local Ollama LLM
When running locally with Ollama, pull the lightweight default `llama3.2:3b` model:
```bash
docker exec -it lenny_ollama ollama pull llama3.2:3b
```
*(Or pull `llama3.1:8b` if you prefer an 8B model: `docker exec -it lenny_ollama ollama pull llama3.1:8b`)*

---

## How to Test the Application

### A. Automated Pytest Suite
Run the complete automated test suite covering ingestion, retrieval ranking, provider routing, FastAPI endpoints, artifact security sanitization, and logging:

```bash
# In your Python virtual environment:
$env:PYTHONPATH="."
python -m pytest -v
```

### B. Retrieval Evaluation CLI
To test vector search relevance across 5 real product/growth questions without invoking LLMs:

```bash
python backend/test_retrieval_cli.py
```

### C. Manual UI Test Plan
Follow the step-by-step end-to-end verification checklist located in [`docs/manual-ui-test-plan.md`](docs/manual-ui-test-plan.md):

1. **Grounded Q&A:** Ask `"How should top PMs think about user activation in PLG products?"` and verify source citation chips.
2. **Grounding Refusal:** Ask an out-of-domain query like `"How do I bake sourdough bread?"` and verify the explicit insufficient grounding response.
3. **Ship 30 Essay:** Enter a topic, click **Ship 30 Essay**, and inspect the rendered Markdown artifact and structure validation status (`✅ PASS`).
4. **Session Management:** Rename a session inline with the `✏️` pencil icon and delete a session with the `🗑️` trash icon.

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@postgres:5432/lenny_assistant` | PostgreSQL + pgvector connection string |
| `LLM_PROVIDER` | `ollama` | Active provider (`ollama` or `anthropic`) |
| `LLM_MODEL` | `llama3.2:3b` | Active model name |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama service endpoint |
| `ANTHROPIC_API_KEY` | *(optional)* | Required only when `LLM_PROVIDER=anthropic` |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | SentenceTransformer embedding model name |

---

## Troubleshooting & FAQs

#### Q: The web interface says `Failed to fetch` or `ERR_EMPTY_RESPONSE`.
- Ensure Docker containers are running: `docker compose ps`.
- Check if port 8000 or 8001 is open: test `http://localhost:8001/config` or `http://localhost:8000/config`.

#### Q: Generating answers locally with Ollama is taking time.
- CPU inference for long-form essays can take 30–60 seconds on standard laptops.
- For sub-3-second responses, set `LLM_PROVIDER=anthropic` and provide an `ANTHROPIC_API_KEY` in `.env`.

