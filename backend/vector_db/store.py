"""Lightweight, file-backed vector store.

Persists to ``backend/data/store.json``. Uses cosine similarity for retrieval.

Why a hand-rolled store: keeps the project dependency-light and easy to inspect.
Swap this module out for FAISS / Chroma / pgvector when scale demands it — the
public API (``add``, ``search``, ``count``, ``clear``) is intentionally minimal.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List

import numpy as np

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "store.json"
_lock = asyncio.Lock()
_cache: Dict | None = None


def _load_sync() -> Dict:
    if not _DATA_FILE.exists():
        return {"items": []}
    try:
        with _DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            return {"items": []}
        return data
    except (json.JSONDecodeError, OSError):
        return {"items": []}


def _persist_sync(data: Dict) -> None:
    _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


async def _ensure_loaded() -> Dict:
    global _cache
    if _cache is not None:
        return _cache
    async with _lock:
        if _cache is None:
            _cache = await asyncio.to_thread(_load_sync)
    return _cache


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


async def add(entries: List[Dict]) -> int:
    """Append entries (each ``{"text": str, "embedding": List[float]}``) to the store."""
    store = await _ensure_loaded()
    now = int(time.time() * 1000)
    for e in entries:
        store["items"].append(
            {
                "id": f"{now}-{uuid.uuid4().hex[:8]}",
                "text": e["text"],
                "embedding": list(e["embedding"]),
                "createdAt": now,
            }
        )
    await asyncio.to_thread(_persist_sync, store)
    return len(store["items"])


async def search(query_embedding: List[float], k: int = 4) -> List[Dict]:
    """Return the top-k most similar items as ``[{"text", "score"}]``."""
    store = await _ensure_loaded()
    if not store["items"]:
        return []

    q = np.asarray(query_embedding, dtype=np.float32)
    scored = []
    for item in store["items"]:
        emb = np.asarray(item["embedding"], dtype=np.float32)
        scored.append({"text": item["text"], "score": _cosine(q, emb)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]


async def count() -> int:
    store = await _ensure_loaded()
    return len(store["items"])


async def clear() -> None:
    global _cache
    _cache = {"items": []}
    await asyncio.to_thread(_persist_sync, _cache)
