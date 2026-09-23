import aio_pika
from aio_pika.abc import AbstractChannel

from app.core.config import Settings


async def declare_topology(channel: AbstractChannel, settings: Settings) -> None:
    events = await channel.declare_exchange(settings.event_exchange, aio_pika.ExchangeType.DIRECT, durable=True)
    retry = await channel.declare_exchange(settings.retry_exchange, aio_pika.ExchangeType.DIRECT, durable=True)
    dlx = await channel.declare_exchange(settings.dead_letter_exchange, aio_pika.ExchangeType.DIRECT, durable=True)

    queue = await channel.declare_queue(settings.event_queue, durable=True)
    await queue.bind(events, routing_key="process")

    retry_queue = await channel.declare_queue(
        settings.retry_queue,
        durable=True,
        arguments={
            "x-message-ttl": settings.retry_delay_ms,
            "x-dead-letter-exchange": settings.event_exchange,
            "x-dead-letter-routing-key": "process",
        },
    )
    await retry_queue.bind(retry, routing_key="retry")

    dlq = await channel.declare_queue(settings.dead_letter_queue, durable=True)
    await dlq.bind(dlx, routing_key="dead")
