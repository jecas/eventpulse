from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.messaging.connection import connect_rabbitmq
from app.messaging.publisher import EventPublisher
from app.messaging.topology import declare_topology
from app.repositories.event import EventRepository
from app.services.event import EventService


async def get_publisher(
    settings: Settings = Depends(get_settings),
) -> AsyncIterator[EventPublisher]:
    connection = await connect_rabbitmq()
    async with connection:
        channel = await connection.channel()
        await declare_topology(channel, settings)
        yield EventPublisher(channel, settings)


def get_event_service(
    session: AsyncSession = Depends(get_session),
    publisher: EventPublisher = Depends(get_publisher),
) -> EventService:
    return EventService(EventRepository(session), publisher)
