import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EventStatus(enum.StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status", values_callable=lambda enum: [item.value for item in enum]),
        nullable=False,
        default=EventStatus.QUEUED,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
