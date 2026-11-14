from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.student import StudentProfile
from app.modules.engagement.repository import StudentProfileRepository
from app.modules.engagement.schemas import StudentProfileInput, StudentProfileResponse


class StudentProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = StudentProfileRepository(session)

    async def upsert(
        self,
        student_hash: str,
        profile_input: StudentProfileInput,
    ) -> StudentProfileResponse:
        profile = await self._repository.get(student_hash)
        values = profile_input.model_dump()

        if profile is None:
            profile = StudentProfile(student_hash=student_hash, **values)
            self._repository.add(profile)
        else:
            for field, value in values.items():
                setattr(profile, field, value)

        await self._session.commit()
        await self._session.refresh(profile)
        return StudentProfileResponse.model_validate(profile)
