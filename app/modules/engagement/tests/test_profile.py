from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, decode_access_token
from app.main import app
from app.modules.engagement.router import get_student_profile_service
from app.modules.engagement.schemas import StudentProfileInput, StudentProfileResponse

_TEST_SECRET = "test-only-secret-that-is-at-least-32-characters"


@dataclass
class FakeProfile:
    interests: list[str]
    goal: str
    availability: list[str]
    budget_pref: int | None
    year_type: str | None


class FakeProfileService:
    def __init__(self) -> None:
        self.profiles: dict[str, FakeProfile] = {}

    async def upsert(
        self,
        student_hash: str,
        profile_input: StudentProfileInput,
    ) -> StudentProfileResponse:
        self.profiles[student_hash] = FakeProfile(**profile_input.model_dump())
        return StudentProfileResponse.model_validate(self.profiles[student_hash])


def _student_token(student_hash: str = "a" * 64) -> str:
    return create_access_token(student_hash, "student", _TEST_SECRET)


def test_demo_auth_returns_signed_student_token() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/auth/demo")

    assert response.status_code == 200
    result = response.json()
    claims = decode_access_token(result["access_token"], _TEST_SECRET)
    assert result["token_type"] == "bearer"
    assert result["expires_in"] == 3600
    assert claims.role == "student"
    assert len(claims.subject) == 64


def test_profile_requires_student_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://unused")
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)

    with TestClient(app) as client:
        response = client.post("/v1/profile", json={"goal": "Find friends"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_profile_is_saved_for_token_identity_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://unused")
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    fake_service = FakeProfileService()
    app.dependency_overrides[get_student_profile_service] = lambda: fake_service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/profile",
                headers={"Authorization": f"Bearer {_student_token()}"},
                json={
                    "interests": ["music"],
                    "goal": "Meet people",
                    "availability": ["Thursday evening"],
                    "budget_pref": 20,
                    "year_type": "undergraduate",
                },
            )
    finally:
        app.dependency_overrides.pop(get_student_profile_service, None)

    assert response.status_code == 200
    assert response.json() == {
        "interests": ["music"],
        "goal": "Meet people",
        "availability": ["Thursday evening"],
        "budget_pref": 20,
        "year_type": "undergraduate",
    }
    assert "student_hash" not in response.json()
    assert set(fake_service.profiles) == {"a" * 64}


def test_profile_rejects_invalid_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://unused")
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)

    with TestClient(app) as client:
        response = client.post(
            "/v1/profile",
            headers={"Authorization": "Bearer invalid.token.value"},
            json={"goal": "Find friends"},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_profile_rejects_org_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://unused")
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)

    org_token = create_access_token("org-id", "org", _TEST_SECRET)
    with TestClient(app) as client:
        response = client.post(
            "/v1/profile",
            headers={"Authorization": f"Bearer {org_token}"},
            json={"goal": "Find friends"},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
