import os
from typing import List, Dict, Any, Optional
import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5435/lenny_assistant")

_cached_model = None

def get_embedding_model():
    global _cached_model
    if _cached_model is None:
        _cached_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _cached_model

class RetrievalService:
    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME, db_url: str = DATABASE_URL):
        self.db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    def get_connection(self):
        conn = psycopg.connect(self.db_url)
        register_vector(conn)
        return conn

    def retrieve(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        model = get_embedding_model()
        query_vector = model.encode(query).tolist()
        
        conn = self.get_connection()
        results = []
        with conn.cursor() as cur:
            cur.execute("""
            SELECT 
                id, episode_slug, episode_title, guest_name, source_path,
                approx_timestamp, chunk_index, content,
                1 - (embedding <=> %s::vector) AS similarity
            FROM transcript_chunks
            ORDER BY embedding <=> %s::vector ASC
            LIMIT %s;
            """, (query_vector, query_vector, top_k))
            
            rows = cur.fetchall()
            for row in rows:
                results.append({
                    "id": str(row[0]),
                    "episode_slug": row[1],
                    "episode_title": row[2],
                    "guest_name": row[3],
                    "source_path": row[4],
                    "approx_timestamp": row[5],
                    "chunk_index": row[6],
                    "content": row[7],
                    "relevance_score": float(row[8])
                })
        conn.close()

        if results:
            top_scores = [r["relevance_score"] for r in results[:min(3, len(results))]]
            aggregate_score = float(np.mean(top_scores))
        else:
            aggregate_score = 0.0

        return {
            "query": query,
            "aggregate_score": aggregate_score,
            "chunks": results
        }
