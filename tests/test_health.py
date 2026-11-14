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


def test_swagger_and_openapi_include_student_routes() -> None:
    with TestClient(app) as client:
        docs_response = client.get("/docs")
        openapi_response = client.get("/openapi.json")

    assert docs_response.status_code == 200
    assert openapi_response.status_code == 200
    paths = openapi_response.json()["paths"]
    assert "/v1/auth/demo" in paths
    assert "/v1/profile" in paths
