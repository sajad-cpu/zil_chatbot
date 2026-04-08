"""FastAPI entrypoint for the RAG chatbot backend.

Run with:
    uvicorn main:app --reload --port 5000
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env BEFORE importing route modules so they see GEMINI_API_KEY.
load_dotenv()

from routes.chat import router as chat_router  # noqa: E402
from routes.train import router as train_router  # noqa: E402

app = FastAPI(title="RAG Chatbot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "service": "rag-chatbot-backend"}


app.include_router(train_router)
app.include_router(chat_router)


@app.on_event("startup")
async def _startup_warning() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "[server] WARNING: GEMINI_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )
