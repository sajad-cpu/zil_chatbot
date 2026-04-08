"""Async wrapper around the Gemini REST API.

Uses ``httpx.AsyncClient`` so FastAPI handlers can ``await`` calls without
blocking the event loop. No SDK dependency — just plain HTTP.
"""

from __future__ import annotations

import os
from typing import List

import httpx

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and add your key."
        )
    return key


def _embed_model() -> str:
    return os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")


def _chat_model() -> str:
    return os.environ.get("GEMINI_CHAT_MODEL", "gemini-2.5-flash-lite")


async def embed_text(text: str) -> List[float]:
    """Embed a single text input via Gemini's embedContent endpoint."""
    model = _embed_model()
    url = f"{BASE_URL}/models/{model}:embedContent?key={_api_key()}"
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
    """Call Gemini generateContent with a fully constructed RAG prompt."""
    model = _chat_model()
    url = f"{BASE_URL}/models/{model}:generateContent?key={_api_key()}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.9,
            "maxOutputTokens": 1024,
        },
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        res = await client.post(url, json=payload)

    if res.status_code != 200:
        raise RuntimeError(f"Gemini generate failed ({res.status_code}): {res.text}")

    data = res.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Gemini generate response missing text: {data}") from exc

    return text.strip()
