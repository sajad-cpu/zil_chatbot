"""Conversation management routes.

GET    /conversations         → list user's conversations
POST   /conversations         → create new conversation
DELETE /conversations/{id}    → delete conversation
GET    /conversations/{id}    → get conversation with last 6 messages
"""

from __future__ import annotations

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from db.pool import get_pool
from auth.deps import get_current_user

router = APIRouter(prefix="/conversations", tags=["conversations"])


class MessageItem(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: str
    messages: List[MessageItem]


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str


class CreateConversationRequest(BaseModel):
    title: str = "New Chat"


@router.get("", response_model=List[ConversationSummary])
async def list_conversations(
    user_id: Annotated[str, Depends(get_current_user)],
) -> List[ConversationSummary]:
    """List all conversations for the current user."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, title, created_at
            FROM conversations
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user_id,
        )

    return [
        ConversationSummary(
            id=str(row["id"]),
            title=row["title"],
            created_at=row["created_at"].isoformat(),
        )
        for row in rows
    ]


@router.post("", response_model=ConversationSummary)
async def create_conversation(
    req: CreateConversationRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> ConversationSummary:
    """Create a new conversation for the current user."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        conversation = await conn.fetchrow(
            """
            INSERT INTO conversations (user_id, title)
            VALUES ($1, $2)
            RETURNING id, title, created_at
            """,
            user_id,
            req.title,
        )

    return ConversationSummary(
        id=str(conversation["id"]),
        title=conversation["title"],
        created_at=conversation["created_at"].isoformat(),
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    user_id: Annotated[str, Depends(get_current_user)],
) -> ConversationDetail:
    """Get a conversation with its last 6 messages."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Verify ownership
        conversation = await conn.fetchrow(
            """
            SELECT id, title, created_at
            FROM conversations
            WHERE id = $1 AND user_id = $2
            """,
            conversation_id,
            user_id,
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        # Get last 6 messages
        messages = await conn.fetch(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
            LIMIT 6
            """,
            conversation_id,
        )

    return ConversationDetail(
        id=str(conversation["id"]),
        title=conversation["title"],
        created_at=conversation["created_at"].isoformat(),
        messages=[
            MessageItem(
                id=str(msg["id"]),
                role=msg["role"],
                content=msg["content"],
                created_at=msg["created_at"].isoformat(),
            )
            for msg in messages
        ],
    )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    """Delete a conversation (and all its messages)."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Verify ownership and delete
        result = await conn.execute(
            """
            DELETE FROM conversations
            WHERE id = $1 AND user_id = $2
            """,
            conversation_id,
            user_id,
        )

        # Check if anything was deleted
        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

    return {"ok": True}
