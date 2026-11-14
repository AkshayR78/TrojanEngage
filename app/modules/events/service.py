from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.event import Event
from app.modules.events.repository import EventRepository
from app.modules.events.schemas import EventCreate, EventResponse


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = EventRepository(session)

    async def create(self, org_id: UUID, event_input: EventCreate) -> EventResponse:
        values = event_input.model_dump(exclude={"type"})
        event = Event(
            org_id=org_id,
            event_type=event_input.type,
            **values,
        )
        self._repository.add(event)
        await self._session.commit()
        await self._session.refresh(event)
        return EventResponse.model_validate(event)

    async def publish(self, event_id: UUID, org_id: UUID) -> EventResponse:
        event = await self._get_owned(event_id, org_id)
        if event.status == "published":
            return EventResponse.model_validate(event)
        if event.status != "draft":
            raise AppError("INVALID_EVENT_STATUS", "Only draft events can be published", 409)

        event.status = "published"
        await self._session.commit()
        await self._session.refresh(event)
        return EventResponse.model_validate(event)

    async def get_live(self, event_id: UUID, org_id: UUID) -> EventResponse:
        event = await self._get_owned(event_id, org_id)
        if event.status not in ("published", "live"):
            raise AppError("EVENT_NOT_LIVE", "Event is not published or live", 409)
        return EventResponse.model_validate(event)

    async def close(self, event_id: UUID, org_id: UUID) -> EventResponse:
        event = await self._get_owned(event_id, org_id)
        if event.status == "closed":
            return EventResponse.model_validate(event)
        if event.status not in ("published", "live"):
            raise AppError("INVALID_EVENT_STATUS", "Only published events can be closed", 409)

        event.status = "closed"
        await self._session.commit()
        await self._session.refresh(event)
        return EventResponse.model_validate(event)

    async def _get_owned(self, event_id: UUID, org_id: UUID) -> Event:
        event = await self._repository.get_owned(event_id, org_id)
        if event is None:
            raise AppError("NOT_FOUND", "Event not found", 404)
        return event
