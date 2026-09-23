# EventPulse

EventPulse is an event-driven processing service built with Python, FastAPI, RabbitMQ, PostgreSQL and Redis.

It demonstrates reliable asynchronous processing patterns: API-to-queue handoff, background consumers, retry queues, dead-letter routing, idempotent processing, persistence, correlation IDs and full-stack end-to-end testing.

## Architecture

```text
Client
  |
  v
FastAPI --persist--> PostgreSQL
  |
  | publish
  v
RabbitMQ
  |
  v
Worker ----dedup----> Redis
  |
  +----call---------> Mock External API
  |
  +----status-------> PostgreSQL
  |
  +----retry--------> Retry Queue
  |
  +----exhausted----> Dead Letter Queue
```

## Event lifecycle

`queued → processing → completed`

Transient failures use a retry queue:

`queued → processing → retrying → processing → completed`

After the configured maximum attempts:

`queued → processing → retrying → ... → failed → DLQ`

## Key features

- FastAPI endpoint returning `202 Accepted`
- Durable RabbitMQ exchanges and queues
- Async worker with `aio-pika`
- Retry queue with TTL-based delayed redelivery
- Dead-letter queue
- Redis-based consumer deduplication
- PostgreSQL event lifecycle persistence
- Async SQLAlchemy and Alembic
- Correlation ID propagation
- Structured JSON logging
- Mock external service
- Docker Compose stack
- Unit and full-stack E2E tests
- GitHub Actions CI

## Run locally

```bash
docker compose up --build
```

API: `http://localhost:8000`

Swagger: `http://localhost:8000/docs`

RabbitMQ management UI: `http://localhost:15672`

Default RabbitMQ credentials for the development stack are `eventpulse` / `eventpulse`.

## Testing

```bash
ruff check .
pytest -v
```

The GitHub Actions E2E job starts PostgreSQL, RabbitMQ, Redis, the API, worker and mock external service, then validates successful processing, retry-and-recovery, and exhausted-retry failure behavior.

## Stack

Python 3.12 · FastAPI · aio-pika · RabbitMQ · PostgreSQL · SQLAlchemy · asyncpg · Redis · Alembic · HTTPX · Docker · Pytest · Ruff · GitHub Actions

## Status

EventPulse is currently pre-release (`0.1.0`). A stable `v1.0.0` release will be created after the complete CI and E2E pipeline is validated.
