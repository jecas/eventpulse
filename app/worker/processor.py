import httpx
import redis.asyncio as redis

from app.core.config import Settings
from app.models.event import Event, EventStatus
from app.repositories.event import EventRepository


class EventProcessor:
    def __init__(
        self,
        repository: EventRepository,
        redis_client: redis.Redis,
        http_client: httpx.AsyncClient,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._redis = redis_client
        self._http = http_client
        self._settings = settings

    async def process(self, event: Event, attempt: int) -> bool:
        dedup_key = f"eventpulse:processed:{event.id}"
        if await self._redis.exists(dedup_key):
            return True

        await self._repository.update_status(
            event,
            EventStatus.PROCESSING,
            attempts=attempt + 1,
            last_error=None,
        )

        try:
            response = await self._http.post(
                f"{self._settings.external_api_url.rstrip('/')}/process",
                json={
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                    "payload": event.payload,
                },
                headers={"X-Correlation-ID": event.correlation_id},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            status = (
                EventStatus.RETRYING
                if attempt + 1 < self._settings.max_attempts
                else EventStatus.FAILED
            )
            await self._repository.update_status(
                event,
                status,
                attempts=attempt + 1,
                last_error=str(exc)[:500],
            )
            return False

        await self._redis.set(dedup_key, "1", ex=self._settings.dedup_ttl_seconds)
        await self._repository.update_status(
            event,
            EventStatus.COMPLETED,
            attempts=attempt + 1,
            last_error=None,
        )
        return True
