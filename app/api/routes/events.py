from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_event_service
from app.schemas.event import EventAccepted, EventCreate, EventRead
from app.services.event import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_event(
    body: EventCreate,
    request: Request,
    service: EventService = Depends(get_event_service),
) -> EventAccepted:
    return await service.create(body, request.state.correlation_id)


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: UUID,
    service: EventService = Depends(get_event_service),
) -> EventRead:
    event = await service.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
