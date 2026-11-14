from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.organization import Organization
from app.modules.auth.repository import OrganizationRepository


class DemoAuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._organizations = OrganizationRepository(session)

    async def create_demo_organization(self, name: str) -> UUID:
        organization = Organization(name=name)
        self._organizations.add(organization)
        await self._session.commit()
        await self._session.refresh(organization)
        return organization.id
