from uuid import UUID

from app.messaging.publisher import EventPublisher
from app.repositories.event import EventRepository
from app.schemas.event import EventAccepted, EventCreate, EventRead


class EventService:
    def __init__(self, repository: EventRepository, publisher: EventPublisher) -> None:
        self._repository = repository
        self._publisher = publisher

    async def create(self, request: EventCreate, correlation_id: str) -> EventAccepted:
        event = await self._repository.create(
            event_type=request.event_type,
            payload=request.payload,
            correlation_id=correlation_id,
        )
        await self._publisher.publish(str(event.id), correlation_id)
        return EventAccepted(
            event_id=str(event.id),
            status=event.status.value,
            correlation_id=correlation_id,
        )

    async def get(self, event_id: UUID) -> EventRead | None:
        event = await self._repository.get(event_id)
        if event is None:
            return None
        return EventRead(
            event_id=str(event.id),
            event_type=event.event_type,
            status=event.status.value,
            attempts=event.attempts,
            correlation_id=event.correlation_id,
            last_error=event.last_error,
        )
