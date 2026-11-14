from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import StudentPrincipal, require_student
from app.db.session import get_session
from app.modules.engagement.schemas import StudentProfileInput, StudentProfileResponse
from app.modules.engagement.service import StudentProfileService

router = APIRouter(prefix="/v1", tags=["student"])


def get_student_profile_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StudentProfileService:
    return StudentProfileService(session)


@router.post("/profile", response_model=StudentProfileResponse)
async def save_student_profile(
    profile_input: StudentProfileInput,
    principal: Annotated[StudentPrincipal, Depends(require_student)],
    service: Annotated[StudentProfileService, Depends(get_student_profile_service)],
) -> StudentProfileResponse:
    return await service.upsert(principal.student_hash, profile_input)
