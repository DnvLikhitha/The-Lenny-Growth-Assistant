import os
import json
import uuid
import time
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from backend.database import (
    init_app_db, create_session, list_sessions, get_session,
    delete_session, save_message, save_artifact, get_artifact
)
from backend.providers.factory import get_model_provider
from backend.providers.base import ProviderError
from backend.retrieval import RetrievalService
from backend.agent.orchestrator import AgentOrchestrator
from backend.ingest import run_ingestion

app = FastAPI(title="The Lenny Growth Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = AgentOrchestrator()

@app.on_event("startup")
def startup_event():
    try:
        init_app_db()
    except Exception as e:
        print(f"Warning: DB initialization during startup failed: {e}")

# Request Models
class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Chat"

class SendMessageRequest(BaseModel):
    content: str
    intent: Optional[str] = "answer_question"  # answer_question | write_ship30_essay | generate_artifact

class CreateArtifactRequest(BaseModel):
    kind: str = "markdown"  # markdown | html
    prompt: str

# Envelope Helper
def make_envelope(data: Any = None, error: Optional[Dict[str, Any]] = None):
    return {"data": data, "error": error}

# Endpoints
@app.get("/health")
def health_check():
    return make_envelope({"status": "ok"})

@app.get("/health/ready")
def readiness_check():
    provider_str = os.getenv("LLM_PROVIDER", "ollama")
    model_str = os.getenv("LLM_MODEL", "llama3.1:8b")
    
    db_ok = False
    try:
        from backend.database import get_db_connection
        conn = get_db_connection()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False

    provider_ok = False
    try:
        provider = get_model_provider(provider_str, model_str)
        provider_ok = provider.is_available()
    except Exception:
        provider_ok = False

    if not db_ok or not provider_ok:
        return JSONResponse(
            status_code=503,
            content=make_envelope(
                data={"db_ready": db_ok, "provider_ready": provider_ok},
                error={
                    "code": "SERVICE_UNREADY",
                    "message": "Service readiness checks failed.",
                    "detail": {"db_ready": db_ok, "provider_ready": provider_ok}
                }
            )
        )
    return make_envelope({"db_ready": True, "provider_ready": True, "status": "ready"})

@app.get("/config")
def get_config():
    provider_str = os.getenv("LLM_PROVIDER", "ollama")
    model_str = os.getenv("LLM_MODEL", "llama3.1:8b")
    return make_envelope({
        "active_provider": provider_str,
        "active_model": model_str
    })

@app.post("/sessions")
def api_create_session(req: CreateSessionRequest):
    provider_str = os.getenv("LLM_PROVIDER", "ollama")
    sess = create_session(title=req.title or "New Chat", provider=provider_str)
    return make_envelope(sess)

@app.get("/sessions")
def api_list_sessions():
    sessions = list_sessions()
    return make_envelope(sessions)

@app.get("/sessions/{session_id}")
def api_get_session(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return make_envelope(sess)

@app.delete("/sessions/{session_id}")
def api_delete_session(session_id: str):
    success = delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return make_envelope({"deleted": True})

@app.post("/sessions/{session_id}/messages")
async def api_send_message(session_id: str, req: SendMessageRequest):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    # Save user message
    user_msg = save_message(session_id=session_id, role="user", content=req.content)

    # Format history for provider
    history = []
    for m in sess.get("messages", []):
        history.append({"role": m["role"], "content": m["content"]})

    # Prepare SSE stream
    async def event_generator():
        retrieved_chunks = []
        aggregate_score = 0.0
        full_assistant_content = ""
        latency_ms = 0
        provider_name = ""
        insufficient_grounding = False

        try:
            async for event in orchestrator.answer_question(
                query=req.content,
                history=history,
                provider_type=os.getenv("LLM_PROVIDER"),
                model_name=os.getenv("LLM_MODEL")
            ):
                if event["type"] == "retrieval":
                    aggregate_score = event["aggregate_score"]
                    retrieved_chunks = event["chunks"]
                    yield f"event: retrieval\ndata: {json.dumps(event)}\n\n"
                elif event["type"] == "content":
                    full_assistant_content += event["delta"]
                    yield f"event: content\ndata: {json.dumps(event)}\n\n"
                elif event["type"] == "done":
                    full_assistant_content = event["content"]
                    latency_ms = event.get("latency_ms", 0)
                    provider_name = event.get("provider", "unknown")
                    insufficient_grounding = event.get("insufficient_grounding", False)

            # Persist assistant message & citations
            asst_msg = save_message(
                session_id=session_id,
                role="assistant",
                content=full_assistant_content,
                provider=provider_name,
                model_name=os.getenv("LLM_MODEL"),
                latency_ms=latency_ms,
                retrieval_score=aggregate_score,
                citations=retrieved_chunks if not insufficient_grounding else []
            )

            done_payload = {
                "message_id": asst_msg["id"],
                "content": full_assistant_content,
                "retrieval_score": aggregate_score,
                "latency_ms": latency_ms,
                "insufficient_grounding": insufficient_grounding,
                "citations": asst_msg.get("citations", [])
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

        except ProviderError as pe:
            err_data = {"code": pe.code, "message": pe.message, "detail": pe.detail}
            yield f"event: error\ndata: {json.dumps(err_data)}\n\n"
        except Exception as e:
            err_data = {"code": "INTERNAL_ERROR", "message": str(e)}
            yield f"event: error\ndata: {json.dumps(err_data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/sessions/{session_id}/artifacts")
async def api_generate_artifact(session_id: str, req: CreateArtifactRequest):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get last assistant message or user prompt
    messages = sess.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="Cannot generate artifact for empty session.")

    last_msg_id = messages[-1]["id"]

    try:
        res = await orchestrator.write_ship30_essay(
            topic=req.prompt,
            provider_type=os.getenv("LLM_PROVIDER"),
            model_name=os.getenv("LLM_MODEL")
        )

        art = save_artifact(
            message_id=last_msg_id,
            kind=res["kind"],
            content=res["content"],
            word_count=res["word_count"],
            structure_valid=res["structure_valid"]
        )
        return make_envelope(art)
    except ProviderError as pe:
        raise HTTPException(status_code=502, detail={"code": pe.code, "message": pe.message})

@app.get("/artifacts/{artifact_id}")
def api_get_artifact(artifact_id: str):
    art = get_artifact(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return make_envelope(art)

@app.post("/ingest/run")
def api_run_ingest(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_ingestion)
    return make_envelope({"status": "ingestion_triggered"})
