import pytest
import psycopg
from backend.retrieval import RetrievalService
from backend.ingest import get_db_connection_sync, init_db

def test_retrieval_service_calculation():
    service = RetrievalService()
    res = service.retrieve("product activation", top_k=3)
    
    assert "query" in res
    assert res["query"] == "product activation"
    assert "aggregate_score" in res
    assert "chunks" in res
    assert isinstance(res["aggregate_score"], float)
    
    if res["chunks"]:
        first_chunk = res["chunks"][0]
        assert "episode_title" in first_chunk
        assert "guest_name" in first_chunk
        assert "source_path" in first_chunk
        assert "approx_timestamp" in first_chunk
        assert "relevance_score" in first_chunk

def test_idempotent_ingestion_db():
    conn = get_db_connection_sync()
    init_db()
    
    dummy_source = "tests/fixtures/sample_episode.md"
    dummy_chunk_idx = 99999
    
    with conn.cursor() as cur:
        # First upsert
        cur.execute("""
        INSERT INTO transcript_chunks (
            episode_slug, episode_title, guest_name, source_path,
            approx_timestamp, chunk_index, content, embedding
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_path, chunk_index) DO UPDATE SET
            content = EXCLUDED.content;
        """, ("test-slug", "Test Title", "Test Guest", dummy_source, "00:00:00", dummy_chunk_idx, "Initial content", [0.1]*384))
        
        # Count rows
        cur.execute("SELECT COUNT(*) FROM transcript_chunks WHERE source_path = %s AND chunk_index = %s;", (dummy_source, dummy_chunk_idx))
        count_1 = cur.fetchone()[0]
        
        # Second upsert (same key)
        cur.execute("""
        INSERT INTO transcript_chunks (
            episode_slug, episode_title, guest_name, source_path,
            approx_timestamp, chunk_index, content, embedding
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_path, chunk_index) DO UPDATE SET
            content = EXCLUDED.content;
        """, ("test-slug", "Test Title", "Test Guest", dummy_source, "00:00:00", dummy_chunk_idx, "Updated content", [0.1]*384))
        
        cur.execute("SELECT COUNT(*) FROM transcript_chunks WHERE source_path = %s AND chunk_index = %s;", (dummy_source, dummy_chunk_idx))
        count_2 = cur.fetchone()[0]
        
        # Cleanup
        cur.execute("DELETE FROM transcript_chunks WHERE source_path = %s AND chunk_index = %s;", (dummy_source, dummy_chunk_idx))
        
    conn.close()
    
    assert count_1 == 1
    assert count_2 == 1
