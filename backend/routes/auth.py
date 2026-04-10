"""Authentication routes: signup, login, and current user.

POST /auth/signup → creates user, returns JWT
POST /auth/login → authenticates, returns JWT
GET  /auth/me    → returns current user info (requires JWT)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from db.pool import get_pool
from auth.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str


class MeResponse(BaseModel):
    user_id: str
    email: str


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against its hash."""
    return pwd_context.verify(plain, hashed)


def _create_access_token(user_id: str) -> str:
    """Create a JWT token for the given user_id."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expires}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest) -> AuthResponse:
    """Create a new user account and return JWT."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Check if email already exists
        existing = await conn.fetchval(
            "SELECT id FROM users WHERE email = $1",
            req.email,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        # Insert new user
        password_hash = _hash_password(req.password)
        user_id = await conn.fetchval(
            """
            INSERT INTO users (email, password_hash)
            VALUES ($1, $2)
            RETURNING id
            """,
            req.email,
            password_hash,
        )

    # Create and return JWT
    access_token = _create_access_token(str(user_id))
    return AuthResponse(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest) -> AuthResponse:
    """Authenticate user and return JWT."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Fetch user by email
        user = await conn.fetchrow(
            "SELECT id, password_hash FROM users WHERE email = $1",
            req.email,
        )

        if not user or not _verify_password(req.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

    # Create and return JWT
    access_token = _create_access_token(str(user["id"]))
    return AuthResponse(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=MeResponse)
async def me(user_id: Annotated[str, Depends(get_current_user)]) -> MeResponse:
    """Get current user info (requires valid JWT)."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email FROM users WHERE id = $1",
            user_id,
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

    return MeResponse(user_id=str(user["id"]), email=user["email"])
