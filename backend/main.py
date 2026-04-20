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

from db.migrations import init_db  # noqa: E402
from routes.auth import router as auth_router  # noqa: E402
from routes.chat import router as chat_router  # noqa: E402
from routes.conversations import router as conversations_router  # noqa: E402
from routes.train import router as train_router  # noqa: E402

app = FastAPI(title="RAG Chatbot", version="1.0.0")

# CORS: allow frontend origins (comma-separated) + always allow localhost for dev
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
origins = [u.strip() for u in frontend_url.split(",") if u.strip()]
if "http://localhost:5173" not in origins:
    origins.append("http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "service": "rag-chatbot-backend"}


app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(train_router)
app.include_router(chat_router)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database and warn about missing env vars."""
    await init_db()

    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "[server] WARNING: GEMINI_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )

    if not os.environ.get("JWT_SECRET"):
        print(
            "[server] WARNING: JWT_SECRET is not set. "
            "Set a secure random string in .env (e.g. openssl rand -hex 32)."
        )
