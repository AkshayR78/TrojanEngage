from dataclasses import dataclass
from typing import Literal

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import TokenError, decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class StudentPrincipal:
    student_hash: str
    role: Literal["student"]


async def require_student(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> StudentPrincipal:
    if credentials is None:
        raise AppError("UNAUTHORIZED", "A bearer token is required", 401)

    try:
        claims = decode_access_token(
            credentials.credentials,
            settings.jwt_secret.get_secret_value(),
        )
    except TokenError as exc:
        raise AppError("UNAUTHORIZED", "The access token is invalid or expired", 401) from exc

    if claims.role != "student":
        raise AppError("FORBIDDEN", "A student access token is required", 403)

    return StudentPrincipal(student_hash=claims.subject, role="student")
