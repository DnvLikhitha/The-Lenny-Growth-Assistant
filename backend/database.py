import os
import uuid
import psycopg
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5435/lenny_assistant")

def get_db_connection():
    url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg.connect(url, autocommit=True)
    return conn

def init_app_db():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            display_name TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """)
        
        # sessions table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            active_provider TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """)

        # messages table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            provider TEXT,
            model_name TEXT,
            latency_ms INT,
            retrieval_score FLOAT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """)

        # transcript_chunks table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS transcript_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            episode_slug TEXT NOT NULL,
            episode_title TEXT NOT NULL,
            guest_name TEXT NOT NULL,
            source_path TEXT NOT NULL,
            approx_timestamp TEXT,
            chunk_index INT NOT NULL,
            content TEXT NOT NULL,
            embedding vector(384),
            UNIQUE(source_path, chunk_index)
        );
        """)

        # message_citations table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS message_citations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
            chunk_id UUID REFERENCES transcript_chunks(id) ON DELETE SET NULL,
            relevance_score FLOAT NOT NULL
        );
        """)

        # artifacts table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS artifacts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            content TEXT NOT NULL,
            word_count INT NOT NULL,
            structure_valid BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """)

        # Seed default user if none exists
        cur.execute("SELECT id FROM users LIMIT 1;")
        if not cur.fetchone():
            cur.execute("INSERT INTO users (id, display_name) VALUES ('00000000-0000-0000-0000-000000000001'::uuid, 'Default User');")
            
    conn.close()

# Session CRUD operations
def create_session(title: str = "New Chat", provider: str = "ollama") -> Dict[str, Any]:
    conn = get_db_connection()
    session_id = str(uuid.uuid4())
    default_user_id = '00000000-0000-0000-0000-000000000001'
    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO sessions (id, user_id, title, active_provider, created_at, updated_at)
        VALUES (%s, %s, %s, %s, NOW(), NOW())
        RETURNING id, user_id, title, active_provider, created_at, updated_at;
        """, (session_id, default_user_id, title, provider))
        row = cur.fetchone()
        res = {
            "id": str(row[0]),
            "user_id": str(row[1]),
            "title": row[2],
            "active_provider": row[3],
            "created_at": row[4].isoformat(),
            "updated_at": row[5].isoformat()
        }
    conn.close()
    return res

def list_sessions() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    sessions = []
    with conn.cursor() as cur:
        cur.execute("""
        SELECT id, user_id, title, active_provider, created_at, updated_at
        FROM sessions ORDER BY updated_at DESC;
        """)
        for row in cur.fetchall():
            sessions.append({
                "id": str(row[0]),
                "user_id": str(row[1]),
                "title": row[2],
                "active_provider": row[3],
                "created_at": row[4].isoformat(),
                "updated_at": row[5].isoformat()
            })
    conn.close()
    return sessions

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
        SELECT id, user_id, title, active_provider, created_at, updated_at
        FROM sessions WHERE id = %s;
        """, (session_id,))
        s_row = cur.fetchone()
        if not s_row:
            conn.close()
            return None
        
        # Get messages with citations
        cur.execute("""
        SELECT id, session_id, role, content, provider, model_name, latency_ms, retrieval_score, created_at
        FROM messages WHERE session_id = %s ORDER BY created_at ASC;
        """, (session_id,))
        m_rows = cur.fetchall()
        
        messages = []
        for m in m_rows:
            msg_id = str(m[0])
            # Fetch citations for message
            cur.execute("""
            SELECT mc.id, mc.chunk_id, mc.relevance_score, tc.episode_title, tc.guest_name, tc.source_path, tc.approx_timestamp
            FROM message_citations mc
            LEFT JOIN transcript_chunks tc ON mc.chunk_id = tc.id
            WHERE mc.message_id = %s;
            """, (msg_id,))
            cit_rows = cur.fetchall()
            citations = []
            for c in cit_rows:
                citations.append({
                    "id": str(c[0]),
                    "chunk_id": str(c[1]) if c[1] else None,
                    "relevance_score": float(c[2]),
                    "episode_title": c[3],
                    "guest_name": c[4],
                    "source_path": c[5],
                    "approx_timestamp": c[6]
                })
                
            messages.append({
                "id": msg_id,
                "session_id": str(m[1]),
                "role": m[2],
                "content": m[3],
                "provider": m[4],
                "model_name": m[5],
                "latency_ms": m[6],
                "retrieval_score": float(m[7]) if m[7] is not None else None,
                "created_at": m[8].isoformat(),
                "citations": citations
            })

        res = {
            "id": str(s_row[0]),
            "user_id": str(s_row[1]),
            "title": s_row[2],
            "active_provider": s_row[3],
            "created_at": s_row[4].isoformat(),
            "updated_at": s_row[5].isoformat(),
            "messages": messages
        }
    conn.close()
    return res

def delete_session(session_id: str) -> bool:
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE id = %s RETURNING id;", (session_id,))
        deleted = cur.fetchone()
    conn.close()
    return bool(deleted)

def save_message(
    session_id: str,
    role: str,
    content: str,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    latency_ms: Optional[int] = None,
    retrieval_score: Optional[float] = None,
    citations: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    conn = get_db_connection()
    msg_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO messages (id, session_id, role, content, provider, model_name, latency_ms, retrieval_score, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        RETURNING id, created_at;
        """, (msg_id, session_id, role, content, provider, model_name, latency_ms, retrieval_score))
        row = cur.fetchone()
        created_at = row[1].isoformat()

        # Update session title if first message & title is default
        if role == "user":
            cur.execute("SELECT title FROM sessions WHERE id = %s;", (session_id,))
            st = cur.fetchone()
            if st and st[0] == "New Chat":
                new_title = content[:30] + "..." if len(content) > 30 else content
                cur.execute("UPDATE sessions SET title = %s, updated_at = NOW() WHERE id = %s;", (new_title, session_id))

        saved_citations = []
        if citations:
            for cit in citations:
                chunk_id = cit.get("id")
                rel_score = cit.get("relevance_score", 0.0)
                cur.execute("""
                INSERT INTO message_citations (message_id, chunk_id, relevance_score)
                VALUES (%s, %s, %s)
                RETURNING id;
                """, (msg_id, chunk_id, rel_score))
                cit_id = str(cur.fetchone()[0])
                saved_citations.append({
                    "id": cit_id,
                    "chunk_id": chunk_id,
                    "relevance_score": rel_score,
                    "episode_title": cit.get("episode_title"),
                    "guest_name": cit.get("guest_name"),
                    "source_path": cit.get("source_path"),
                    "approx_timestamp": cit.get("approx_timestamp")
                })

    conn.close()
    return {
        "id": msg_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "provider": provider,
        "model_name": model_name,
        "latency_ms": latency_ms,
        "retrieval_score": retrieval_score,
        "created_at": created_at,
        "citations": saved_citations
    }

def save_artifact(
    message_id: str,
    kind: str,
    content: str,
    word_count: int,
    structure_valid: bool
) -> Dict[str, Any]:
    conn = get_db_connection()
    art_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO artifacts (id, message_id, kind, content, word_count, structure_valid, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        RETURNING id, created_at;
        """, (art_id, message_id, kind, content, word_count, structure_valid))
        row = cur.fetchone()
        created_at = row[1].isoformat()
    conn.close()
    return {
        "id": art_id,
        "message_id": message_id,
        "kind": kind,
        "content": content,
        "word_count": word_count,
        "structure_valid": structure_valid,
        "created_at": created_at
    }

def get_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
        SELECT id, message_id, kind, content, word_count, structure_valid, created_at
        FROM artifacts WHERE id = %s;
        """, (artifact_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None
        res = {
            "id": str(row[0]),
            "message_id": str(row[1]),
            "kind": row[2],
            "content": row[3],
            "word_count": row[4],
            "structure_valid": row[5],
            "created_at": row[6].isoformat()
        }
    conn.close()
    return res
