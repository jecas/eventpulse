from fastapi import FastAPI

from app.api.routes import events, health
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware

settings = get_settings()
configure_logging()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Reliable event-driven processing service.",
)
app.add_middleware(CorrelationIdMiddleware)
app.include_router(health.router)
app.include_router(events.router, prefix=settings.api_prefix)
