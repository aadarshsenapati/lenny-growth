import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import SessionNotFoundError
from app.db.database import get_db
from app.db.models import ChatSession, Message
from app.db.schemas import MessageResponse, SessionCreateRequest, SessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(payload: SessionCreateRequest, db: AsyncSession = Depends(get_db)) -> SessionResponse:
    settings = get_settings()
    session = ChatSession(
        title=payload.title or "New chat",
        user_id=payload.user_id,
        llm_provider=payload.llm_provider or settings.llm_provider,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SessionResponse.model_validate(session)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(user_id: str = "anonymous", db: AsyncSession = Depends(get_db)) -> list[SessionResponse]:
    result = await db.execute(
        select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc())
    )
    sessions = result.scalars().all()
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SessionResponse:
    session = await db.get(ChatSession, session_id)
    if not session:
        raise SessionNotFoundError(f"Session {session_id} not found.")
    return SessionResponse.model_validate(session)


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_session_messages(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[MessageResponse]:
    session = await db.get(ChatSession, session_id)
    if not session:
        raise SessionNotFoundError(f"Session {session_id} not found.")
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    )
    messages = result.scalars().all()
    return [MessageResponse.model_validate(m) for m in messages]


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    session = await db.get(ChatSession, session_id)
    if not session:
        raise SessionNotFoundError(f"Session {session_id} not found.")
    await db.delete(session)
    await db.commit()
