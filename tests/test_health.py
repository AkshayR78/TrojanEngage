from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok_and_request_id() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_http_errors_use_standard_shape_and_request_id() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/missing")

    error = response.json()["error"]
    assert response.status_code == 404
    assert set(error) == {"code", "message", "request_id"}
    assert error["code"] == "NOT_FOUND"
    assert error["request_id"] == response.headers["X-Request-ID"]
