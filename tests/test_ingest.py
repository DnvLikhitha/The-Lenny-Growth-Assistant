import pytest
from pathlib import Path
from backend.ingest import parse_transcript_metadata, chunk_transcript

SAMPLE_TRANSCRIPT = """---
title: "Product-Led Growth Masterclass with Elena Verna"
guest: "Elena Verna"
---

# Product-Led Growth Masterclass with Elena Verna

Elena Verna (00:01:15):
Product-led growth is non-linear. The most important levers for user activation are seamless onboarding experiences, self-serve value realization, and friction removal.

Lenny Rachitsky (00:03:40):
What are the biggest mistakes teams make when transitioning from sales-led to product-led growth?

Elena Verna (00:04:10):
The biggest mistake is assuming that PLG is just a self-serve tier. It requires a complete rethink of product taxonomy, user analytics, and cross-functional alignment across growth, marketing, and engineering.
"""

def test_parse_transcript_metadata(tmp_path):
    # Setup test file
    repo_dir = tmp_path / "repo"
    episodes_dir = repo_dir / "episodes" / "elena-verna"
    episodes_dir.mkdir(parents=True)
    file_path = episodes_dir / "transcript.md"
    file_path.write_text(SAMPLE_TRANSCRIPT, encoding="utf-8")

    # Patch REPO_DIR behavior by calculating relative path manually or with test input
    from backend import ingest
    old_repo_dir = ingest.REPO_DIR
    ingest.REPO_DIR = repo_dir
    try:
        metadata, body = parse_transcript_metadata(file_path)
        assert metadata["episode_slug"] == "elena-verna"
        assert metadata["episode_title"] == "Product-Led Growth Masterclass with Elena Verna"
        assert metadata["guest_name"] == "Elena Verna"
        assert metadata["source_path"] == "episodes/elena-verna/transcript.md"
        assert "Product-led growth is non-linear" in body
    finally:
        ingest.REPO_DIR = old_repo_dir

def test_chunk_transcript():
    body = "Para 1 text [00:01:00] with some content.\n\nPara 2 text [00:02:30] with more content.\n\nPara 3 text [00:04:00] with even more content."
    chunks = chunk_transcript(body, min_chunk_words=5, max_chunk_words=15)
    
    assert len(chunks) > 0
    assert "approx_timestamp" in chunks[0]
    assert "content" in chunks[0]
    # Check timestamp anchor extraction
    assert chunks[0]["approx_timestamp"] in ["00:01:00", "00:02:30", "00:04:00"]
