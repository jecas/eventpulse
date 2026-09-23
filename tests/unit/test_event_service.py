from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.event import EventStatus
from app.schemas.event import EventCreate
from app.services.event import EventService


class FakeRepository:
    async def create(self, **kwargs):
        return SimpleNamespace(id=uuid4(), status=EventStatus.QUEUED)


class FakePublisher:
    def __init__(self):
        self.published = None

    async def publish(self, event_id, correlation_id, attempt=0):
        self.published = (event_id, correlation_id, attempt)


@pytest.mark.asyncio
async def test_service_persists_then_publishes():
    publisher = FakePublisher()
    service = EventService(FakeRepository(), publisher)
    result = await service.create(
        EventCreate(event_type="customer.notification", payload={"message": "hello"}),
        "corr-123",
    )
    assert result.status == "queued"
    assert result.correlation_id == "corr-123"
    assert publisher.published[0] == result.event_id
