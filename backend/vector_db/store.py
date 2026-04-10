"""Postgres-backed vector store using pgvector.

Persists to Supabase (or any Postgres with pgvector extension).
Uses cosine similarity for retrieval.

Set DATABASE_URL in .env:
    DATABASE_URL=postgresql://user:password@host:port/database
"""

from __future__ import annotations

from typing import Dict, List

from db.pool import get_pool


async def add(entries: List[Dict]) -> int:
    """Append entries (each ``{"text": str, "embedding": List[float]}``) to the store."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Ensure pgvector extension exists
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        except Exception as e:
            print(f"Warning creating vector extension: {e}")

        # Ensure table exists (idempotent)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    text text NOT NULL,
                    embedding vector(3072) NOT NULL,
                    created_at timestamptz NOT NULL DEFAULT now()
                )
            """)
        except Exception as e:
            print(f"Warning creating table: {e}")
            if "already exists" not in str(e).lower():
                raise

        # Ensure index exists (idempotent)
        # Note: Using hnsw for 3072-dimensional vectors (ivfflat limited to 2000 dims)
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
                    ON rag_chunks
                    USING hnsw (embedding vector_cosine_ops)
            """)
        except Exception as e:
            # If hnsw not available, fall back to btree (slower but works)
            try:
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
                        ON rag_chunks (embedding)
                """)
            except Exception:
                pass  # Index creation failed, searches will still work but be slower

        # Insert entries
        for e in entries:
            await conn.execute(
                """
                INSERT INTO rag_chunks (text, embedding)
                VALUES ($1, $2)
                """,
                e["text"],
                e["embedding"],
            )

        # Return total count
        count_result = await conn.fetchval("SELECT COUNT(*) FROM rag_chunks")
        return count_result or 0


async def search(query_embedding: List[float], k: int = 4) -> List[Dict]:
    """Return the top-k most similar items as ``[{"text", "score"}]``."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Cosine similarity search using pgvector's <=> operator
        rows = await conn.fetch(
            """
            SELECT text, 1 - (embedding <=> $1) AS score
            FROM rag_chunks
            ORDER BY embedding <=> $1
            LIMIT $2
            """,
            query_embedding,
            k,
        )

        return [{"text": row["text"], "score": float(row["score"])} for row in rows]


async def count() -> int:
    """Return the total number of chunks."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Check if table exists first
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'rag_chunks'
            )
        """)

        if not exists:
            return 0

        result = await conn.fetchval("SELECT COUNT(*) FROM rag_chunks")
        return result or 0


async def clear() -> None:
    """Wipe the entire store."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM rag_chunks")
