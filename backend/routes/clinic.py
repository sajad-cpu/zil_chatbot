"""Clinic AI routes for the integrated appointment-booking flow."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth.deps import get_current_user
from services.clinic_agent import create_session, process_message

router = APIRouter(prefix="/clinic", tags=["clinic"])


class ClinicSessionResponse(BaseModel):
    session_id: str
    state: dict[str, Any]


class ClinicMessageRequest(BaseModel):
    session_id: str | None = None
    message: str


@router.post("/session", response_model=ClinicSessionResponse)
async def new_clinic_session(
    user_id: Annotated[str, Depends(get_current_user)],
) -> ClinicSessionResponse:
    session_id, state = create_session(user_id)
    return ClinicSessionResponse(session_id=session_id, state=state)


@router.post("/message", response_model=ClinicSessionResponse)
async def clinic_message(
    req: ClinicMessageRequest,
    user_id: Annotated[str, Depends(get_current_user)],
) -> ClinicSessionResponse:
    session_id, state = process_message(user_id, req.session_id, req.message)
    return ClinicSessionResponse(session_id=session_id, state=state)
