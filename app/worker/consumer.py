import json
import logging
from uuid import UUID

import aio_pika
import httpx
import redis.asyncio as redis
from aio_pika.abc import (
    AbstractChannel,
    AbstractIncomingMessage,
    AbstractRobustConnection,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.messaging.topology import declare_topology
from app.repositories.event import EventRepository
from app.worker.processor import EventProcessor

logger = logging.getLogger(__name__)


class EventConsumer:
    def __init__(
        self,
        connection: AbstractRobustConnection,
        session_factory: async_sessionmaker[AsyncSession],
        redis_client: redis.Redis,
        http_client: httpx.AsyncClient,
        settings: Settings,
    ) -> None:
        self._connection = connection
        self._session_factory = session_factory
        self._redis = redis_client
        self._http = http_client
        self._settings = settings
        self._channel: AbstractChannel | None = None

    async def start(self) -> None:
        self._channel = await self._connection.channel()

        await self._channel.set_qos(prefetch_count=10)
        await declare_topology(
            self._channel,
            self._settings,
        )

        queue = await self._channel.get_queue(
            self._settings.event_queue,
        )

        await queue.consume(self._handle)

    async def _handle(
        self,
        message: AbstractIncomingMessage,
    ) -> None:
        async with message.process(requeue=False):
            data = json.loads(message.body)

            event_id = UUID(data["event_id"])
            attempt = int(data.get("attempt", 0))

            async with self._session_factory() as session:
                repository = EventRepository(session)

                event = await repository.get(event_id)

                if event is None:
                    logger.warning(
                        "Event %s no longer exists",
                        event_id,
                    )
                    return

                processor = EventProcessor(
                    repository,
                    self._redis,
                    self._http,
                    self._settings,
                )

                success = await processor.process(
                    event,
                    attempt,
                )

                if success:
                    return

                await self._publish_failed_attempt(
                    data=data,
                    event=event,
                    attempt=attempt,
                )

    async def _publish_failed_attempt(
        self,
        *,
        data: dict,
        event,
        attempt: int,
    ) -> None:
        if self._channel is None:
            raise RuntimeError(
                "Consumer channel is not initialized"
            )

        next_attempt = attempt + 1
        data["attempt"] = next_attempt

        if next_attempt < self._settings.max_attempts:
            exchange = await self._channel.get_exchange(
                self._settings.retry_exchange
            )
            routing_key = "retry"

            logger.info(
                "Scheduling event retry",
                extra={
                    "event_id": str(event.id),
                    "correlation_id": event.correlation_id,
                    "attempt": next_attempt,
                },
            )

        else:
            exchange = await self._channel.get_exchange(
                self._settings.dead_letter_exchange
            )
            routing_key = "dead"

            logger.warning(
                "Event moved to dead-letter queue",
                extra={
                    "event_id": str(event.id),
                    "correlation_id": event.correlation_id,
                    "attempt": next_attempt,
                },
            )

        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(data).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                correlation_id=event.correlation_id,
                content_type="application/json",
            ),
            routing_key=routing_key,
        )
