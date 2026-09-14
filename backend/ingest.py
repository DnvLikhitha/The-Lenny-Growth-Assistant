import os
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import git
import psycopg
from psycopg.types.json import Jsonb
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

# Embedding model config (384 dims, fast, accurate local embedding)
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
TRANSCRIPTS_REPO_URL = os.getenv("TRANSCRIPTS_REPO_URL", "https://github.com/ChatPRD/lennys-podcast-transcripts")
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
REPO_DIR = DATA_DIR / "lennys-podcast-transcripts"

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5435/lenny_assistant")

def init_db():
    conn = get_db_connection_sync()
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_transcript_chunks_episode_slug ON transcript_chunks(episode_slug);")
    conn.close()

def get_db_connection_sync():
    # Helper to convert asyncpg URL or standard postgres URL for psycopg3 sync execution
    url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg.connect(url, autocommit=True)
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    register_vector(conn)
    return conn

def sync_transcripts_repo() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if REPO_DIR.exists():
        print(f"Syncing existing repo at {REPO_DIR}...")
        repo = git.Repo(REPO_DIR)
        repo.remotes.origin.pull()
    else:
        print(f"Cloning transcripts repo from {TRANSCRIPTS_REPO_URL}...")
        git.Repo.clone_from(TRANSCRIPTS_REPO_URL, REPO_DIR)
    return REPO_DIR

def parse_transcript_metadata(file_path: Path) -> Tuple[Dict[str, str], str]:
    content = file_path.read_text(encoding="utf-8")
    
    # Extract episode slug from parent folder or filename
    episode_slug = file_path.parent.name if file_path.parent.name != "episodes" else file_path.stem
    
    metadata = {
        "episode_slug": episode_slug,
        "episode_title": episode_slug.replace("-", " ").title(),
        "guest_name": "Unknown Guest",
        "source_path": str(file_path.relative_to(REPO_DIR)).replace("\\", "/")
    }
    
    # Try parsing title/guest from YAML frontmatter or first headings
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    body = content
    if frontmatter_match:
        fm_text = frontmatter_match.group(1)
        body = content[frontmatter_match.end():]
        for line in fm_text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lower()
                v = v.strip().strip("\"'")
                if k in ("title", "episode_title"):
                    metadata["episode_title"] = v
                elif k in ("guest", "guest_name"):
                    metadata["guest_name"] = v
    else:
        # Fallback: check first header # Episode Title or Guest Name
        lines = content.splitlines()
        for line in lines[:10]:
            if line.startswith("# "):
                title = line.replace("# ", "").strip()
                metadata["episode_title"] = title
                if " with " in title:
                    parts = title.split(" with ")
                    metadata["guest_name"] = parts[1].strip()
                elif ":" in title:
                    metadata["guest_name"] = title.split(":")[0].strip()
                break

    return metadata, body

def chunk_transcript(body: str, min_chunk_words: int = 300, max_chunk_words: int = 700) -> List[Dict[str, Any]]:
    # Split into paragraphs/sections preserving timestamps like [00:12:34] or (00:12:34)
    paragraphs = re.split(r'\n\s*\n', body)
    
    chunks = []
    current_words = []
    current_word_count = 0
    current_timestamp = "00:00"
    
    timestamp_regex = re.compile(r'[\[\(](\d{1,2}:\d{2}(?::\d{2})?)[\]\)]')

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue
            
        # Check for timestamp anchor
        ts_match = timestamp_regex.search(para_clean)
        if ts_match:
            current_timestamp = ts_match.group(1)
            
        words = para_clean.split()
        word_count = len(words)
        
        if current_word_count + word_count > max_chunk_words and current_words:
            chunk_text = " ".join(current_words)
            chunks.append({
                "content": chunk_text,
                "approx_timestamp": current_timestamp
            })
            # Overlap last paragraph if feasible
            current_words = words
            current_word_count = word_count
        else:
            current_words.extend(words)
            current_word_count += word_count
            
    if current_words:
        chunks.append({
            "content": " ".join(current_words),
            "approx_timestamp": current_timestamp
        })
        
    return chunks

def run_ingestion():
    print("Initializing database schema...")
    init_db()
    
    repo_path = sync_transcripts_repo()
    episodes_dir = repo_path / "episodes"
    
    if not episodes_dir.exists():
        # Fallback search for any .md files
        transcript_files = list(repo_path.glob("**/*.md"))
    else:
        transcript_files = list(episodes_dir.glob("**/*.md"))
        
    print(f"Found {len(transcript_files)} transcript files.")
    
    print(f"Loading embedding model '{EMBEDDING_MODEL_NAME}'...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    conn = get_db_connection_sync()
    total_chunks = 0
    
    with conn.cursor() as cur:
        for idx, file_path in enumerate(transcript_files, 1):
            metadata, body = parse_transcript_metadata(file_path)
            raw_chunks = chunk_transcript(body)
            if not raw_chunks:
                continue
                
            contents = [c["content"] for c in raw_chunks]
            embeddings = model.encode(contents, batch_size=32, show_progress_bar=False).tolist()
            
            for chunk_idx, (c_obj, emb) in enumerate(zip(raw_chunks, embeddings)):
                cur.execute("""
                INSERT INTO transcript_chunks (
                    episode_slug, episode_title, guest_name, source_path,
                    approx_timestamp, chunk_index, content, embedding
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_path, chunk_index) DO UPDATE SET
                    episode_slug = EXCLUDED.episode_slug,
                    episode_title = EXCLUDED.episode_title,
                    guest_name = EXCLUDED.guest_name,
                    approx_timestamp = EXCLUDED.approx_timestamp,
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding;
                """, (
                    metadata["episode_slug"],
                    metadata["episode_title"],
                    metadata["guest_name"],
                    metadata["source_path"],
                    c_obj["approx_timestamp"],
                    chunk_idx,
                    c_obj["content"],
                    emb
                ))
                total_chunks += 1
                
            if idx % 20 == 0 or idx == len(transcript_files):
                print(f"Processed [{idx}/{len(transcript_files)}] files ({total_chunks} chunks total)")
                
    conn.close()
    print(f"Ingestion complete! Total chunks stored: {total_chunks}")

if __name__ == "__main__":
    run_ingestion()
