from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EventPulse"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://eventpulse:eventpulse@postgres:5432/eventpulse"
    rabbitmq_url: str = "amqp://eventpulse:eventpulse@rabbitmq:5672/"
    redis_url: str = "redis://redis:6379/0"
    external_api_url: str = "http://mock-external:9000"
    event_exchange: str = "eventpulse.events"
    event_queue: str = "eventpulse.events.process"
    retry_exchange: str = "eventpulse.retry"
    retry_queue: str = "eventpulse.events.retry"
    dead_letter_exchange: str = "eventpulse.dlx"
    dead_letter_queue: str = "eventpulse.events.dlq"
    max_attempts: int = 3
    retry_delay_ms: int = 1000
    external_timeout_seconds: float = 5.0
    dedup_ttl_seconds: int = 86400

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
