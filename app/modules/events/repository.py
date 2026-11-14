from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.event import Event


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, event: Event) -> None:
        self._session.add(event)

    async def get_owned(self, event_id: UUID, org_id: UUID) -> Event | None:
        statement = select(Event).where(Event.id == event_id, Event.org_id == org_id)
        return await self._session.scalar(statement)
