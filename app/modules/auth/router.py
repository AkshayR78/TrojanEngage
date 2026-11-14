from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.security import create_access_token, create_demo_student_identity

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class DemoAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


@router.post("/demo", response_model=DemoAuthResponse)
async def create_demo_student_token(
    settings: Settings = Depends(get_settings),
) -> DemoAuthResponse:
    student_hash = create_demo_student_identity()
    access_token = create_access_token(
        student_hash,
        "student",
        settings.jwt_secret.get_secret_value(),
    )
    return DemoAuthResponse(access_token=access_token)
