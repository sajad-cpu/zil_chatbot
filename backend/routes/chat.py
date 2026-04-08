"""Chat endpoint — RAG-based question answering.

Flow:
    1. Embed user query
    2. Cosine-similarity search over the vector store (top-k)
    3. Construct a strict, grounded prompt
    4. Call Gemini to generate the answer
    5. Return answer + the chunks used as evidence
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.gemini import embed_text, generate_answer
from vector_db import store

router = APIRouter(prefix="/chat", tags=["chat"])

TOP_K = 4
# Below this similarity score we treat the chunk as irrelevant noise.
MIN_SCORE = 0.35


class HistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: Optional[List[HistoryItem]] = None


class Source(BaseModel):
    text: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]


def _build_prompt(question: str, context_chunks: List[dict], history: List[HistoryItem]) -> str:
    context_block = "\n\n".join(
        f"[{i + 1}] {c['text']}" for i, c in enumerate(context_chunks)
    ) or "(no context available)"

    history_block = ""
    if history:
        recent = history[-6:]  # last 3 turns
        lines = [
            f"{'User' if h.role == 'user' else 'Assistant'}: {h.content}"
            for h in recent
        ]
        history_block = "Conversation so far:\n" + "\n".join(lines) + "\n"

    parts = [
        "You are a helpful assistant. Answer ONLY using the context below.",
        'If the answer is not present in the context, reply exactly: "I don\'t know".',
        "Do not invent facts. Be concise and direct.",
        "",
        "Context:",
        context_block,
        "",
    ]
    if history_block:
        parts.append(history_block)
    parts.extend(
        [
            f"Question:\n{question}",
            "",
            "Answer:",
        ]
    )
    return "\n".join(parts)


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="'message' must be non-empty")

    # Empty store → graceful response (no API call needed).
    if await store.count() == 0:
        return ChatResponse(
            answer=(
                "I don't know — no knowledge has been added yet. "
                "Use the Teach tab to train me first."
            ),
            sources=[],
        )

    # 1. Embed the query
    try:
        query_embedding = await embed_text(message)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # 2. Top-k retrieval
    hits = await store.search(query_embedding, TOP_K)
    relevant = [h for h in hits if h["score"] >= MIN_SCORE]

    # If nothing crosses the relevance bar, short-circuit before calling the LLM.
    if not relevant:
        return ChatResponse(answer="I don't know", sources=[])

    # 3. Build grounded prompt
    prompt = _build_prompt(message, relevant, req.history or [])

    # 4. Call the LLM
    try:
        answer = await generate_answer(prompt)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponse(
        answer=answer,
        sources=[Source(text=r["text"], score=round(r["score"], 4)) for r in relevant],
    )
