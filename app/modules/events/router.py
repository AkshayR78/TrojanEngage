from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import OrganizationPrincipal, require_organization
from app.db.session import get_session
from app.modules.events.schemas import EventCreate, EventResponse
from app.modules.events.service import EventService

router = APIRouter(prefix="/v1/events", tags=["events"])


def get_event_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EventService:
    return EventService(session)


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_input: EventCreate,
    principal: Annotated[OrganizationPrincipal, Depends(require_organization)],
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventResponse:
    return await service.create(principal.org_id, event_input)


@router.post("/{event_id}/publish", response_model=EventResponse)
async def publish_event(
    event_id: UUID,
    principal: Annotated[OrganizationPrincipal, Depends(require_organization)],
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventResponse:
    return await service.publish(event_id, principal.org_id)


@router.get("/{event_id}/live", response_model=EventResponse)
async def get_live_event(
    event_id: UUID,
    principal: Annotated[OrganizationPrincipal, Depends(require_organization)],
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventResponse:
    return await service.get_live(event_id, principal.org_id)


@router.post("/{event_id}/close", response_model=EventResponse)
async def close_event(
    event_id: UUID,
    principal: Annotated[OrganizationPrincipal, Depends(require_organization)],
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventResponse:
    return await service.close(event_id, principal.org_id)
