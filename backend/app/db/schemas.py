import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------- Sessions ----------
class SessionCreateRequest(BaseModel):
    user_id: str = "anonymous"
    llm_provider: Literal["groq", "ollama"] | None = None
    title: str | None = None


class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    user_id: str
    llm_provider: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------- Chat ----------
class Citation(BaseModel):
    source: str
    episode: str | None = None
    chunk_id: str
    score: float


class ChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str = Field(min_length=1, max_length=8000)
    llm_provider: Literal["groq", "ollama"] | None = None  # per-request override


class ChatResponse(BaseModel):
    message_id: uuid.UUID
    session_id: uuid.UUID
    role: Literal["assistant"] = "assistant"
    content: str
    skill_used: str
    citations: list[Citation] = []
    grounded: bool
    llm_provider: str
    latency_ms: int
    artifact: "ArtifactResponse | None" = None


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    skill_used: str | None
    citations: list[dict] | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Artifacts ----------
class ArtifactResponse(BaseModel):
    id: uuid.UUID
    kind: Literal["markdown", "html"]
    title: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Errors ----------
class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    code: str


# ---------- Health ----------
class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    database: bool
    faiss_index_loaded: bool
    llm_provider: str
    llm_reachable: bool
    ollama_available: bool
