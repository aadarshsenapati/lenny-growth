import uuid
from datetime import datetime

from sqlalchemy import JSON, CHAR, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.database import Base


class UUID(TypeDecorator):
    """Portable UUID type stored as CHAR(36) everywhere (MySQL has no native
    UUID column type either, so this is the same representation in
    production (MySQL) and in the unit-test suite (SQLite) -- no
    dialect-specific branching needed."""

    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class ChatSession(Base):
    """One independent conversation context. Each session has its own
    message history and does not leak context into other sessions."""

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), default="New chat")
    user_id: Mapped[str] = mapped_column(String(255), default="anonymous", index=True)  # simple user metadata, no auth in v1
    llm_provider: Mapped[str] = mapped_column(String(32), default="groq")
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant" | "system"
    content: Mapped[str] = mapped_column(Text)
    skill_used: Mapped[str | None] = mapped_column(String(64), nullable=True)  # e.g. "grounded_qa", "ship30", "artifact"
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)  # list of {source, episode, chunk_id}
    llm_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now(), index=True)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class Artifact(Base):
    """Generated Markdown / HTML artifacts, stored so they can be reloaded
    into the Artifact Viewer after a page refresh."""

    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(16))  # "markdown" | "html"
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
