from typing import Any

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any]


class EventAccepted(BaseModel):
    event_id: str
    status: str
    correlation_id: str


class EventRead(BaseModel):
    event_id: str
    event_type: str
    status: str
    attempts: int
    correlation_id: str
    last_error: str | None = None
