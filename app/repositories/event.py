from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventStatus


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, event_type: str, payload: dict, correlation_id: str) -> Event:
        event = Event(event_type=event_type, payload=payload, correlation_id=correlation_id)
        self._session.add(event)
        await self._session.commit()
        await self._session.refresh(event)
        return event

    async def get(self, event_id: UUID) -> Event | None:
        return await self._session.get(Event, event_id)

    async def update_status(
        self,
        event: Event,
        status: EventStatus,
        *,
        attempts: int | None = None,
        last_error: str | None = None,
    ) -> Event:
        event.status = status
        if attempts is not None:
            event.attempts = attempts
        event.last_error = last_error
        await self._session.commit()
        await self._session.refresh(event)
        return event
