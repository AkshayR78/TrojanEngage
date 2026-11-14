from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import create_access_token, decode_access_token
from app.db.models.event import Event
from app.main import app
from app.modules.auth.router import get_demo_auth_service
from app.modules.events.repository import EventRepository
from app.modules.events.router import get_event_service
from app.modules.events.schemas import EventCreate, EventResponse
from app.modules.events.service import EventService

_TEST_SECRET = "test-only-secret-that-is-at-least-32-characters"


class FakeDemoAuthService:
    def __init__(self) -> None:
        self.organization_name: str | None = None
        self.org_id = uuid4()

    async def create_demo_organization(self, name: str) -> UUID:
        self.organization_name = name
        return self.org_id


class FakeEventService:
    def __init__(self) -> None:
        self.created_for_org: UUID | None = None

    async def create(self, org_id: UUID, event_input: EventCreate) -> EventResponse:
        self.created_for_org = org_id
        return EventResponse.model_validate(
            {
                "id": uuid4(),
                "name": event_input.name,
                "event_type": event_input.type,
                "start_ts": event_input.start_ts,
                "end_ts": event_input.end_ts,
                "venue": event_input.venue,
                "topic_tags": event_input.topic_tags,
                "cost": event_input.cost,
                "budget_planned": event_input.budget_planned,
                "budget_actual": None,
                "expected_size": event_input.expected_size,
                "status": "draft",
            }
        )


class FakeSession(AsyncSession):
    def __init__(self) -> None:
        super().__init__()
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(
        self,
        instance: object,
        attribute_names: Iterable[str] | None = None,
        with_for_update: Any = None,
    ) -> None:
        return None


def _org_token(org_id: UUID) -> str:
    return create_access_token(org_id, "org", _TEST_SECRET)


def test_demo_auth_creates_org_and_returns_org_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://unused")
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    auth_service = FakeDemoAuthService()
    app.dependency_overrides[get_demo_auth_service] = lambda: auth_service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/auth/demo",
                json={"role": "org", "organization_name": "Trojan Student Org"},
            )
    finally:
        app.dependency_overrides.pop(get_demo_auth_service, None)

    assert response.status_code == 200
    result = response.json()
    claims = decode_access_token(result["access_token"], _TEST_SECRET)
    assert result["role"] == "org"
    assert result["org_id"] == str(auth_service.org_id)
    assert auth_service.organization_name == "Trojan Student Org"
    assert claims.role == "org"
    assert claims.org_id == auth_service.org_id


def test_event_creation_uses_org_id_from_token_not_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://unused")
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    org_id = uuid4()
    event_service = FakeEventService()
    app.dependency_overrides[get_event_service] = lambda: event_service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/events",
                headers={"Authorization": f"Bearer {_org_token(org_id)}"},
                json={
                    "org_id": str(uuid4()),
                    "name": "Cultural Night",
                    "type": "social",
                    "start_ts": "2026-12-10T18:00:00Z",
                    "end_ts": "2026-12-10T21:00:00Z",
                    "topic_tags": ["culture"],
                },
            )
    finally:
        app.dependency_overrides.pop(get_event_service, None)

    assert response.status_code == 201
    assert response.json()["status"] == "draft"
    assert event_service.created_for_org == org_id
    assert "org_id" not in response.json()


def test_event_creation_requires_org_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://unused")
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    student_token = create_access_token("a" * 64, "student", _TEST_SECRET)

    with TestClient(app) as client:
        response = client.post(
            "/v1/events",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "name": "Cultural Night",
                "type": "social",
                "start_ts": "2026-12-10T18:00:00Z",
                "end_ts": "2026-12-10T21:00:00Z",
            },
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_publish_changes_draft_event_to_published(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    org_id = uuid4()
    event = Event(
        id=uuid4(),
        org_id=org_id,
        name="Cultural Night",
        event_type="social",
        start_ts=datetime(2026, 12, 10, 18, tzinfo=UTC),
        end_ts=datetime(2026, 12, 10, 21, tzinfo=UTC),
        topic_tags=[],
        headcount=0,
        status="draft",
    )
    session = FakeSession()

    async def get_owned(
        repository: EventRepository,
        event_id: UUID,
        requested_org_id: UUID,
    ) -> Event | None:
        assert requested_org_id == org_id
        return event if event.id == event_id else None

    monkeypatch.setattr(EventRepository, "get_owned", get_owned)
    result = await EventService(session).publish(event.id, org_id)

    assert result.status == "published"
    assert event.status == "published"
    assert session.commits == 1


@pytest.mark.asyncio
async def test_close_changes_published_event_to_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    org_id = uuid4()
    event = Event(
        id=uuid4(),
        org_id=org_id,
        name="Cultural Night",
        event_type="social",
        start_ts=datetime(2026, 12, 10, 18, tzinfo=UTC),
        end_ts=datetime(2026, 12, 10, 21, tzinfo=UTC),
        topic_tags=[],
        headcount=0,
        status="published",
    )
    session = FakeSession()

    async def get_owned(
        repository: EventRepository,
        event_id: UUID,
        requested_org_id: UUID,
    ) -> Event | None:
        assert requested_org_id == org_id
        return event if event.id == event_id else None

    monkeypatch.setattr(EventRepository, "get_owned", get_owned)
    result = await EventService(session).close(event.id, org_id)

    assert result.status == "closed"
    assert session.commits == 1


@pytest.mark.asyncio
async def test_close_rejects_draft_event(monkeypatch: pytest.MonkeyPatch) -> None:
    org_id = uuid4()
    event = Event(
        id=uuid4(),
        org_id=org_id,
        name="Cultural Night",
        event_type="social",
        start_ts=datetime(2026, 12, 10, 18, tzinfo=UTC),
        end_ts=datetime(2026, 12, 10, 21, tzinfo=UTC),
        topic_tags=[],
        headcount=0,
        status="draft",
    )

    async def get_owned(
        repository: EventRepository,
        event_id: UUID,
        requested_org_id: UUID,
    ) -> Event | None:
        return event if event.id == event_id and requested_org_id == org_id else None

    monkeypatch.setattr(EventRepository, "get_owned", get_owned)

    with pytest.raises(AppError) as error:
        await EventService(FakeSession()).close(event.id, org_id)

    assert error.value.code == "INVALID_EVENT_STATUS"
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_event_outside_org_scope_is_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    org_id = uuid4()
    event_id = uuid4()

    async def get_owned(
        repository: EventRepository,
        requested_event_id: UUID,
        requested_org_id: UUID,
    ) -> Event | None:
        assert requested_event_id == event_id
        assert requested_org_id == org_id
        return None

    monkeypatch.setattr(EventRepository, "get_owned", get_owned)

    with pytest.raises(AppError) as error:
        await EventService(FakeSession()).publish(event_id, org_id)

    assert error.value.code == "NOT_FOUND"
    assert error.value.status_code == 404
