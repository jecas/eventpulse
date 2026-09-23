import aio_pika
from aio_pika.abc import AbstractRobustConnection

from app.core.config import get_settings


async def connect_rabbitmq() -> AbstractRobustConnection:
    return await aio_pika.connect_robust(get_settings().rabbitmq_url)
