from fastapi.testclient import TestClient


def test_health_returns_success_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["data"]["appEnv"]
    assert body["data"]["checkedAt"].endswith("+09:00")
    assert body["error"] is None
    assert body["meta"]["requestId"].startswith("req_")
    assert body["meta"]["pagination"] is None


def test_health_is_exposed_in_openapi(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]
