# EventPulse
[![Tests](https://github.com/jecas/eventpulse/actions/workflows/tests.yml/badge.svg)](https://github.com/jecas/eventpulse/actions/workflows/tests.yml)

**Reliable event-driven processing platform built with Python, FastAPI, RabbitMQ, PostgreSQL, and Redis.**

EventPulse is a production-style backend service that demonstrates reliable asynchronous event processing using a message broker and background workers.

Instead of processing work synchronously inside an HTTP request, the API persists an event, publishes it to RabbitMQ, and immediately returns `202 Accepted`. A separate worker consumes the event, performs the external operation, persists processing state, retries transient failures, and routes permanently failing events to a dead-letter queue.

The project focuses on backend patterns commonly used in distributed and event-driven systems: **message queues, background workers, retries, dead-letter queues, idempotent consumers, persistence, correlation IDs, and end-to-end testing**.

---

## Key Features

- Asynchronous event ingestion with FastAPI
- `202 Accepted` API semantics
- RabbitMQ-based event delivery
- Separate asynchronous worker process
- Durable exchanges and queues
- Retry queue with delayed redelivery
- Dead-letter queue for exhausted retries
- Idempotent event processing
- Redis-based deduplication
- PostgreSQL event lifecycle persistence
- Async SQLAlchemy and asyncpg
- Alembic database migrations
- External service integration with HTTPX
- Correlation ID propagation
- Structured JSON logging
- Graceful asynchronous worker architecture
- Deterministic mock external service
- Docker Compose development environment
- Unit tests
- Full-stack end-to-end tests
- GitHub Actions CI
- Migration validation
- Docker image validation

---

## Architecture

```text
                         ┌───────────────┐
                         │    Client     │
                         └───────┬───────┘
                                 │
                         POST /api/v1/events
                                 │
                                 ▼
                         ┌───────────────┐
                         │    FastAPI    │
                         └───────┬───────┘
                                 │
                    persist + publish event
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
             ┌─────────────┐           ┌─────────────┐
             │ PostgreSQL  │           │  RabbitMQ   │
             └─────────────┘           └──────┬──────┘
                                              │
                                           consume
                                              │
                                              ▼
                                      ┌───────────────┐
                                      │    Worker     │
                                      └───────┬───────┘
                                              │
                           ┌──────────────────┼──────────────────┐
                           ▼                  ▼                  ▼
                    ┌─────────────┐    ┌─────────────┐    ┌──────────────┐
                    │ PostgreSQL  │    │    Redis    │    │ External API │
                    │   status    │    │   dedup     │    │    HTTPX     │
                    └─────────────┘    └─────────────┘    └──────────────┘
```

The API and worker are deliberately separated.

The API is responsible for accepting and publishing work, while the worker performs the asynchronous processing.

---

## Event Processing Flow

A client creates an event using:

```http
POST /api/v1/events
```

Example request:

```json
{
  "event_type": "customer.notification",
  "payload": {
    "customer_id": "customer-123",
    "message": "Your report is ready"
  }
}
```

The API persists the event and publishes a message to RabbitMQ.

It immediately responds with:

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "correlation_id": "7f4431f2-31cb-44c1-b3c4-891f42c35c11"
}
```

The client does not wait for the event to be processed.

The worker independently consumes the message and performs the actual processing.

---

## Event Lifecycle

A successfully processed event follows:

```text
QUEUED
   │
   ▼
PROCESSING
   │
   ▼
COMPLETED
```

If the external operation fails:

```text
QUEUED
   │
   ▼
PROCESSING
   │
   ▼
RETRYING
   │
   ▼
RabbitMQ retry queue
   │
   ▼
PROCESSING
```

After the configured maximum number of attempts:

```text
PROCESSING
   │
   ▼
FAILED
   │
   ▼
Dead Letter Queue
```

The lifecycle is persisted in PostgreSQL so processing state can be inspected independently of RabbitMQ.

---

## RabbitMQ Topology

EventPulse uses three logical message flows.

### Main processing queue

```text
eventpulse.events
        │
        │ routing key: process
        ▼
eventpulse.events.process
```

New events are published here and consumed by the worker.

### Retry queue

```text
eventpulse.retry
        │
        │ routing key: retry
        ▼
eventpulse.events.retry
        │
        │ TTL expires
        ▼
eventpulse.events
        │
        ▼
eventpulse.events.process
```

A failed event is published to the retry queue.

The retry queue uses RabbitMQ TTL and dead-letter routing to return the event to the main processing queue after a delay.

This avoids retry loops inside the worker itself.

### Dead-letter queue

```text
eventpulse.dlx
        │
        │ routing key: dead
        ▼
eventpulse.events.dlq
```

When all configured attempts have been exhausted, the event is marked as failed and routed to the dead-letter queue.

This preserves failed messages for later inspection instead of silently discarding them.

---

## Retry Strategy

The worker tracks the processing attempt inside the message.

For example:

```text
attempt 0
    │
    ├── success ──────────────► COMPLETED
    │
    └── failure
           │
           ▼
       retry queue
           │
           ▼
attempt 1
    │
    ├── success ──────────────► COMPLETED
    │
    └── failure
           │
           ▼
       retry queue
           │
           ▼
attempt 2
    │
    ├── success ──────────────► COMPLETED
    │
    └── failure ──────────────► FAILED → DLQ
```

The maximum number of attempts and retry delay are configurable.

---

## Idempotent Processing

Message brokers can deliver the same message more than once.

EventPulse therefore treats event processing as an idempotent operation.

After successful processing, the worker stores a Redis key:

```text
eventpulse:processed:<event_id>
```

If the same event is delivered again, the worker detects the existing key and skips the external operation.

This prevents duplicate processing while keeping PostgreSQL responsible for persistent event state.

Redis acts as a fast deduplication layer rather than the primary event store.

---

## Event Persistence

Event state is stored in PostgreSQL.

Each event contains:

```text
id
event_type
payload
status
attempts
correlation_id
last_error
created_at
updated_at
```

Example lifecycle:

```text
event created
    │
    ▼
status = queued
attempts = 0
    │
    ▼
worker receives event
    │
    ▼
status = processing
attempts = 1
    │
    ├── success
    │      ▼
    │   completed
    │
    └── failure
           ▼
        retrying
```

The API can therefore expose processing state without querying RabbitMQ.

---

## Query Event Status

Processing state can be retrieved using:

```http
GET /api/v1/events/{event_id}
```

Example response:

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "customer.notification",
  "status": "completed",
  "attempts": 1,
  "correlation_id": "7f4431f2-31cb-44c1-b3c4-891f42c35c11",
  "last_error": null
}
```

For retrying or failed events, `last_error` contains information about the latest processing failure.

---

## Correlation IDs

Every request is associated with a correlation ID.

Clients may provide:

```http
X-Correlation-ID: customer-request-123
```

If no correlation ID is supplied, EventPulse generates one automatically.

The correlation ID is:

```text
HTTP request
      │
      ▼
FastAPI
      │
      ▼
RabbitMQ message
      │
      ▼
Worker
      │
      ▼
External API
```

It is also persisted with the event and returned in the HTTP response.

This makes it possible to trace one logical operation across asynchronous service boundaries.

---

## Structured Logging

Application logs use structured JSON.

Example:

```json
{
  "timestamp": "2026-09-23T12:00:00+00:00",
  "level": "INFO",
  "logger": "app.worker.consumer",
  "message": "Scheduling event retry",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "correlation_id": "customer-request-123",
  "attempt": 1
}
```

Event and correlation identifiers make logs easier to search in centralized logging systems.

---

## Mock External Service

The repository includes a deterministic mock external service used for integration and end-to-end testing.

It supports three useful scenarios.

### Successful processing

A normal payload returns successfully.

```json
{
  "message": "hello"
}
```

### Transient failure

```json
{
  "mode": "fail_once"
}
```

The first request returns `503 Service Unavailable`.

The retry succeeds.

Expected result:

```text
attempt 1 → failure
retry
attempt 2 → success
status → completed
```

### Permanent failure

```json
{
  "mode": "always_fail"
}
```

Every request returns `503 Service Unavailable`.

After the configured maximum attempts:

```text
status → failed
message → dead-letter queue
```

These deterministic scenarios allow retry behavior to be tested without depending on a real external provider.

---

## Running with Docker

The complete system can be started with:

```bash
docker compose up --build
```

Docker Compose starts:

```text
PostgreSQL
RabbitMQ
Redis
Mock External Service
EventPulse API
EventPulse Worker
```

The API is available at:

```text
http://localhost:8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

RabbitMQ Management UI:

```text
http://localhost:15672
```

Development credentials:

```text
username: eventpulse
password: eventpulse
```

---

## Example API Request

Create an event:

```bash
curl -X POST http://localhost:8000/api/v1/events \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: example-request-123" \
  -d '{
    "event_type": "customer.notification",
    "payload": {
      "customer_id": "customer-123",
      "message": "Your report is ready"
    }
  }'
```

Example response:

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "correlation_id": "example-request-123"
}
```

Check processing status:

```bash
curl http://localhost:8000/api/v1/events/550e8400-e29b-41d4-a716-446655440000
```

---

## Testing

### Unit tests

Run:

```bash
pytest -v
```

The test suite covers core event processing behavior including successful processing and duplicate-event handling.

### End-to-End Tests

The E2E test starts the complete Docker Compose architecture and validates real communication between the components.

It verifies three scenarios:

```text
1. Successful event
   API → RabbitMQ → Worker → External API → COMPLETED

2. Transient external failure
   API → Worker → 503
                ↓
            Retry Queue
                ↓
             Worker
                ↓
              200
                ↓
            COMPLETED

3. Permanent external failure
   API → Worker → retries exhausted
                ↓
              FAILED
                ↓
               DLQ
```

This tests the event-processing architecture rather than only isolated Python functions.

---

## Database Migrations

Database schema changes are managed with Alembic.

Apply migrations:

```bash
alembic upgrade head
```

The CI pipeline validates migration reversibility using:

```bash
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

This verifies that migrations can be both applied and rolled back successfully.

---

## Continuous Integration

GitHub Actions runs on every push and pull request.

The pipeline validates:

```text
Lint
  │
  ▼
Alembic upgrade
  │
  ▼
Alembic downgrade
  │
  ▼
Alembic upgrade
  │
  ▼
Unit tests
  │
  ▼
API / Worker Docker build
  │
  ▼
Mock service Docker build
  │
  ▼
Full Docker Compose stack
  │
  ▼
End-to-End tests
```

The E2E environment includes the same infrastructure components used by the application:

- PostgreSQL
- RabbitMQ
- Redis
- FastAPI
- EventPulse worker
- Mock external service

---

## Project Structure

```text
eventpulse/
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── alembic/
│   ├── versions/
│   │   └── 0001_create_events.py
│   └── env.py
│
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── events.py
│   │   │   └── health.py
│   │   └── dependencies.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── middleware.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   │
│   ├── messaging/
│   │   ├── connection.py
│   │   ├── publisher.py
│   │   └── topology.py
│   │
│   ├── models/
│   │   └── event.py
│   │
│   ├── repositories/
│   │   └── event.py
│   │
│   ├── schemas/
│   │   └── event.py
│   │
│   ├── services/
│   │   └── event.py
│   │
│   ├── worker/
│   │   ├── consumer.py
│   │   ├── processor.py
│   │   └── main.py
│   │
│   └── main.py
│
├── mock_external/
│   ├── Dockerfile
│   └── main.py
│
├── scripts/
│   └── e2e_test.py
│
├── tests/
│   └── unit/
│
├── compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## Technology Stack

| Area | Technology |
|---|---|
| Language | Python 3.12 |
| API | FastAPI |
| Message Broker | RabbitMQ |
| RabbitMQ Client | aio-pika |
| Worker | Async Python |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2 |
| Database Driver | asyncpg |
| Cache / Deduplication | Redis |
| HTTP Client | HTTPX |
| Migrations | Alembic |
| Validation | Pydantic |
| Containers | Docker / Docker Compose |
| Testing | Pytest |
| Linting | Ruff |
| CI | GitHub Actions |

---

## Design Goals

EventPulse was built to demonstrate backend engineering patterns that become important once work can no longer be handled reliably inside a single synchronous HTTP request.

The main design goals are:

- decouple request handling from background processing
- make event state observable
- tolerate transient downstream failures
- avoid uncontrolled retry loops
- preserve permanently failing messages
- reduce duplicate processing
- make asynchronous flows traceable
- validate the complete distributed workflow in CI

The result is intentionally more than a queue demo: the API, broker, worker, persistence layer, cache, external dependency, retry mechanism, and tests operate together as one system.

---

## Version

Current stable version:

```text
1.0.0
```

---

## License

MIT
