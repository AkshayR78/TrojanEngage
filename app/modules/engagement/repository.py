from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.student import StudentProfile


class StudentProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, student_hash: str) -> StudentProfile | None:
        statement = select(StudentProfile).where(StudentProfile.student_hash == student_hash)
        return await self._session.scalar(statement)

    def add(self, profile: StudentProfile) -> None:
        self._session.add(profile)
