import aio_pika
from aio_pika.abc import AbstractChannel

from app.core.config import Settings


async def declare_topology(
    channel: AbstractChannel,
    settings: Settings,
) -> None:
    event_exchange = await channel.declare_exchange(
        settings.event_exchange,
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    retry_exchange = await channel.declare_exchange(
        settings.retry_exchange,
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    dead_letter_exchange = await channel.declare_exchange(
        settings.dead_letter_exchange,
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    event_queue = await channel.declare_queue(
        settings.event_queue,
        durable=True,
    )
    await event_queue.bind(
        event_exchange,
        routing_key="process",
    )

    retry_queue = await channel.declare_queue(
        settings.retry_queue,
        durable=True,
        arguments={
            "x-message-ttl": int(settings.retry_delay_ms),
            "x-dead-letter-exchange": settings.event_exchange,
            "x-dead-letter-routing-key": "process",
        },
    )
    await retry_queue.bind(
        retry_exchange,
        routing_key="retry",
    )

    dead_letter_queue = await channel.declare_queue(
        settings.dead_letter_queue,
        durable=True,
    )
    await dead_letter_queue.bind(
        dead_letter_exchange,
        routing_key="dead",
    )
