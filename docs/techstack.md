# Tech Stack Specification — The Lenny Growth Assistant

**Related docs:** [`PRD.md`](./PRD.md) · [`architecture.md`](./architecture.md) · [`design.md`](./design.md)

---

## 🛠️ Technology Stack Overview

The application utilizes a fixed, production-grade stack designed for containerized deployment, fast local vector retrieval, and swappable model inference.

---

## 1. Backend Core

| Layer | Technology | Version | Purpose / Role |
|---|---|---|---|
| **Framework** | FastAPI | `0.110.0+` | Asynchronous Python REST & Server-Sent Events (SSE) streaming API |
| **Server** | Uvicorn | `0.28.0+` | ASGI high-performance server |
| **Database Driver** | Psycopg 3 | `3.1.18+` | Native Python driver with `pgvector` vector extension support |
| **Data Validation** | Pydantic | `2.6.0+` | Schema validation and structured JSON response envelopes |
| **Embedding Engine** | SentenceTransformers | `2.5.0+` | HuggingFace `all-MiniLM-L6-v2` local model (384-dimensional dense vectors) |

---

## 2. Database & Vector Search

| Component | Technology | Purpose / Role |
|---|---|---|
| **Primary Database** | PostgreSQL 16 | Relational storage for users, sessions, messages, citations, and artifacts |
| **Vector Extension** | `pgvector` | Dense vector indexing (`vector(384)`) and cosine distance similarity search (`<=>` operator) |
| **Container Image** | `pgvector/pgvector:pg16` | Standardized PostgreSQL container with pre-built pgvector support |

---

## 3. Model Providers (LLM Abstraction)

| Provider | Model Name | Role |
|---|---|---|
| **Ollama (Default Local)** | `llama3.2:3b` / `llama3.1:8b` | Mandatory local demo path running offline inside containerized network |
| **Anthropic (Cloud Path)** | `claude-3-5-sonnet-20241022` | Cloud LLM provider switchable via `LLM_PROVIDER=anthropic` without code changes |

---

## 4. Frontend Workspace

| Layer | Technology | Purpose / Role |
|---|---|---|
| **Library** | React 18 | Declarative component UI framework |
| **Build Tool** | Vite 5 | Rapid ES module bundler and frontend production builder |
| **Web Server** | Nginx Alpine | Lightweight production web server hosting built static frontend assets |
| **UI Styling** | Modern Light Theme CSS | Modern SaaS design system with CSS custom properties |

---

## 5. Deployment & DevOps

| Tool | Purpose |
|---|---|
| **Docker Compose** | One-command orchestration bringing up `frontend`, `api`, `postgres`, and `ollama` on a shared bridge network (`lenny_network`) |
| **Dockerfiles** | Multi-stage builds for frontend (Node + Nginx) and backend (Python 3.11 slim) |
