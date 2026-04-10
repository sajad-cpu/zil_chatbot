"""Training endpoints.

POST   /train          → ingest a body of text into the vector store
DELETE /train/clear    → wipe the store
GET    /train/stats    → quick health/stats endpoint
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.deps import get_current_user
from services.chunker import chunk_text
from services.gemini import embed_batch
from vector_db import store

router = APIRouter(prefix="/train", tags=["train"])


class TrainRequest(BaseModel):
    content: str = Field(..., min_length=1)


class TrainResponse(BaseModel):
    ok: bool
    chunksAdded: int
    totalChunks: int


class StatsResponse(BaseModel):
    totalChunks: int


@router.post("", response_model=TrainResponse)
async def train(
    req: TrainRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> TrainResponse:
    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="'content' must be non-empty")

    # 1. Split into chunks
    chunks = chunk_text(content)
    if not chunks:
        raise HTTPException(status_code=400, detail="No usable text in 'content'")

    # 2. Embed each chunk
    try:
        embeddings = await embed_batch(chunks)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # 3. Persist
    entries = [{"text": t, "embedding": emb} for t, emb in zip(chunks, embeddings)]
    total = await store.add(entries)

    return TrainResponse(ok=True, chunksAdded=len(chunks), totalChunks=total)


@router.delete("/clear")
async def clear(
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    await store.clear()
    return {"ok": True}


@router.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    return StatsResponse(totalChunks=await store.count())
