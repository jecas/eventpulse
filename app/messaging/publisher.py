import json

import aio_pika
from aio_pika.abc import AbstractChannel

from app.core.config import Settings


class EventPublisher:
    def __init__(self, channel: AbstractChannel, settings: Settings) -> None:
        self._channel = channel
        self._settings = settings

    async def publish(self, event_id: str, correlation_id: str, attempt: int = 0) -> None:
        exchange = await self._channel.get_exchange(self._settings.event_exchange)
        body = json.dumps(
            {"event_id": event_id, "correlation_id": correlation_id, "attempt": attempt}
        ).encode()
        await exchange.publish(
            aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                correlation_id=correlation_id,
                content_type="application/json",
            ),
            routing_key="process",
        )
