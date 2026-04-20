"""Async wrapper around AI APIs.

Embeddings: Gemini REST API (for vector search).
Answer generation: ZilRouter (OpenAI-compatible chat completions API).

Uses ``httpx.AsyncClient`` so FastAPI handlers can ``await`` calls without
blocking the event loop. No SDK dependency — just plain HTTP.
"""

from __future__ import annotations

import os
from typing import List

import httpx

# Gemini config (embeddings only)
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# ZilRouter config (answer generation)
ZILROUTER_BASE_URL = os.environ.get("ZILROUTER_URL", "https://zilrouter.ngrok.app")
_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


def _gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and add your key."
        )
    return key


def _zilrouter_api_key() -> str:
    key = os.environ.get("ZILROUTER_API_KEY")
    if not key:
        raise RuntimeError("ZILROUTER_API_KEY is not set in .env")
    return key


def _embed_model() -> str:
    return os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")


async def embed_text(text: str) -> List[float]:
    """Embed a single text input via Gemini's embedContent endpoint."""
    model = _embed_model()
    url = f"{GEMINI_BASE_URL}/models/{model}:embedContent?key={_gemini_api_key()}"
    payload = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": text}]},
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        res = await client.post(url, json=payload)

    if res.status_code != 200:
        raise RuntimeError(f"Gemini embed failed ({res.status_code}): {res.text}")

    data = res.json()
    values = data.get("embedding", {}).get("values")
    if not isinstance(values, list):
        raise RuntimeError("Gemini embed response missing embedding.values")
    return values


async def embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed an array of texts sequentially (free-tier friendly)."""
    out: List[List[float]] = []
    for t in texts:
        out.append(await embed_text(t))
    return out


async def generate_answer(prompt: str) -> str:
    """Call ZilRouter chat completions API with a fully constructed RAG prompt."""
    url = f"{ZILROUTER_BASE_URL}/api/v1/chat/completions"
    payload = {
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {_zilrouter_api_key()}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        res = await client.post(url, json=payload, headers=headers)

    if res.status_code != 200:
        raise RuntimeError(f"ZilRouter generate failed ({res.status_code}): {res.text}")

    data = res.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"ZilRouter response missing content: {data}") from exc

    return text.strip()
