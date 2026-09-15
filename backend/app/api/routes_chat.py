import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm_provider import get_llm_client
from app.agent.router import detect_artifact_kind, route
from app.agent.skills import artifact_skill, grounded_qa_skill, ship30_skill
from app.core.exceptions import SessionNotFoundError
from app.db.database import get_db
from app.db.models import Artifact, ChatSession, Message
from app.db.schemas import ArtifactResponse, ChatRequest, ChatResponse, Citation
from app.logging_config import get_logger

router = APIRouter(prefix="/chat", tags=["chat"])
log = get_logger(__name__)

HISTORY_TURN_LIMIT = 12  # last N messages included as context, keeps prompts bounded
AUTO_TITLE_LENGTH = 60


async def _load_history(db: AsyncSession, session_id: uuid.UUID) -> list[dict]:
    from sqlalchemy import select

    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at.desc()).limit(HISTORY_TURN_LIMIT)
    )
    messages = list(reversed(result.scalars().all()))
    return [{"role": m.role, "content": m.content} for m in messages]


def _derive_title(message: str) -> str:
    clean = " ".join(message.split())
    if len(clean) <= AUTO_TITLE_LENGTH:
        return clean
    return clean[:AUTO_TITLE_LENGTH].rstrip() + "…"


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    session = await db.get(ChatSession, payload.session_id)
    if not session:
        raise SessionNotFoundError(f"Session {payload.session_id} not found.")

    provider = payload.llm_provider or session.llm_provider
    llm = get_llm_client(provider)
    history = await _load_history(db, session.id)

    skill_name = route(payload.message)
    log.info("skill_routed", skill=skill_name, session_id=str(session.id))

    # Persist the user's message first so it's never lost even if the LLM call fails.
    user_msg = Message(session_id=session.id, role="user", content=payload.message)
    db.add(user_msg)

    # First message in a session gives it a real title instead of "New chat",
    # and every message bumps updated_at so the sidebar orders by recent activity.
    if session.title in (None, "", "New chat") and not history:
        session.title = _derive_title(payload.message)
    session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)  # MySQL DATETIME is naive; store as UTC
    db.add(session)

    await db.commit()

    artifact_payload: ArtifactResponse | None = None
    latency_ms = 0

    if skill_name == "ship30":
        result = await ship30_skill.run(llm, topic=payload.message, conversation_history=history)
        content, citations, grounded = result["content"], result["citations"], result["grounded"]
        latency_ms = result["llm_result"].latency_ms
    elif skill_name == "artifact":
        kind = detect_artifact_kind(payload.message)
        art_result = await artifact_skill.run(
            llm, conversation_history=history, kind=kind, title=payload.message[:120]
        )
        content = f"Here is your {kind} artifact — see the viewer panel."
        citations, grounded = [], True
        latency_ms = art_result["llm_result"].latency_ms
        artifact_row = Artifact(
            session_id=session.id, kind=kind, title=art_result["title"], content=art_result["content"]
        )
        db.add(artifact_row)
        await db.flush()
        artifact_payload = ArtifactResponse.model_validate(artifact_row)
    else:
        result = await grounded_qa_skill.run(llm, user_message=payload.message, conversation_history=history)
        content, citations, grounded = result["content"], result["citations"], result["grounded"]
        latency_ms = result["llm_result"].latency_ms

    assistant_msg = Message(
        session_id=session.id,
        role="assistant",
        content=content,
        skill_used=skill_name,
        citations=citations,
        llm_provider=provider,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return ChatResponse(
        message_id=assistant_msg.id,
        session_id=session.id,
        content=content,
        skill_used=skill_name,
        citations=[Citation(**c) for c in citations],
        grounded=grounded,
        llm_provider=provider,
        latency_ms=latency_ms,
        artifact=artifact_payload,
    )
