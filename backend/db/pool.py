"""Shared asyncpg connection pool with pgvector support.

This module provides a singleton pool that is initialized once and reused
across all DB access. Supports Supabase pgBouncer with statement_cache_size=0.
"""

from __future__ import annotations

import asyncio
import os

import asyncpg
from pgvector.asyncpg import register_vector

_pool: asyncpg.Pool | None = None
_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    """Get or create the shared asyncpg pool."""
    global _pool
    if _pool is not None:
        return _pool

    async with _lock:
        if _pool is not None:
            return _pool

        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Please set it to your Postgres connection string."
            )

        async def init_connection(conn):
            await register_vector(conn)

        _pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
            init=init_connection,
            statement_cache_size=0,  # Disable for pgBouncer compatibility (Supabase pooler)
        )

        return _pool


async def close_pool() -> None:
    """Close the pool (used on shutdown)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
