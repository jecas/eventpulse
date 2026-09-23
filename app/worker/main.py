import asyncio
import logging

import httpx
import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import async_session_factory
from app.messaging.connection import connect_rabbitmq
from app.worker.consumer import EventConsumer

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    configure_logging()
    connection = await connect_rabbitmq()
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)

    async with connection, httpx.AsyncClient(
        timeout=httpx.Timeout(settings.external_timeout_seconds)
    ) as http_client:
        consumer = EventConsumer(
            connection,
            async_session_factory,
            redis_client,
            http_client,
            settings,
        )
        await consumer.start()
        logger.info("EventPulse worker started")
        try:
            await asyncio.Future()
        finally:
            await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(run())
