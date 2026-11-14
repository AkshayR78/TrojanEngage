from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import create_access_token, create_demo_student_identity
from app.db.session import get_session
from app.modules.auth.service import DemoAuthService

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class DemoAuthRequest(BaseModel):
    role: Literal["student", "org"] = "student"
    organization_name: str | None = Field(default=None, min_length=1, max_length=150)

    @model_validator(mode="after")
    def require_organization_name(self) -> "DemoAuthRequest":
        if self.role == "org" and self.organization_name is None:
            raise ValueError("organization_name is required for role 'org'")
        return self


class DemoAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    role: Literal["student", "org"]
    org_id: UUID | None = None


def get_demo_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DemoAuthService:
    return DemoAuthService(session)


@router.post("/demo", response_model=DemoAuthResponse)
async def create_demo_token(
    service: Annotated[DemoAuthService, Depends(get_demo_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    request: DemoAuthRequest | None = None,
) -> DemoAuthResponse:
    auth_request = request or DemoAuthRequest()
    org_id: UUID | None = None
    if auth_request.role == "org":
        if auth_request.organization_name is None:
            raise AppError(
                "VALIDATION_ERROR",
                "organization_name is required for role 'org'",
                422,
            )
        org_id = await service.create_demo_organization(auth_request.organization_name)
        token_identity: str | UUID = org_id
    else:
        token_identity = create_demo_student_identity()

    access_token = create_access_token(
        token_identity,
        auth_request.role,
        settings.jwt_secret.get_secret_value(),
    )
    return DemoAuthResponse(
        access_token=access_token,
        role=auth_request.role,
        org_id=org_id,
    )
