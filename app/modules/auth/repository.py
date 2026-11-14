from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.organization import Organization


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, organization: Organization) -> None:
        self._session.add(organization)
