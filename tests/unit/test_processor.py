from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.core.config import Settings
from app.models.event import EventStatus
from app.worker.processor import EventProcessor


class FakeRepository:
    def __init__(self):
        self.statuses = []

    async def update_status(self, event, status, **kwargs):
        event.status = status
        event.attempts = kwargs.get("attempts", getattr(event, "attempts", 0))
        self.statuses.append(status)
        return event


class FakeRedis:
    def __init__(self, exists=False):
        self._exists = exists
        self.saved = False

    async def exists(self, key):
        return self._exists

    async def set(self, key, value, ex=None):
        self.saved = True


@pytest.mark.asyncio
async def test_processor_completes_event():
    def handler(request):
        return httpx.Response(200, json={"status": "processed"})

    event = SimpleNamespace(
        id=uuid4(),
        event_type="customer.notification",
        payload={},
        correlation_id="corr-1",
        attempts=0,
        status=EventStatus.QUEUED,
    )
    repo = FakeRepository()
    cache = FakeRedis()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        processor = EventProcessor(
            repo,
            cache,
            client,
            Settings(external_api_url="https://external.test"),
        )
        assert await processor.process(event, 0) is True

    assert repo.statuses == [EventStatus.PROCESSING, EventStatus.COMPLETED]
    assert cache.saved is True


@pytest.mark.asyncio
async def test_processor_skips_duplicate():
    event = SimpleNamespace(id=uuid4())
    repo = FakeRepository()
    cache = FakeRedis(exists=True)

    async with httpx.AsyncClient() as client:
        processor = EventProcessor(repo, cache, client, Settings())
        assert await processor.process(event, 0) is True

    assert repo.statuses == []
