from fastapi.testclient import TestClient


def test_not_found_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/missing")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["meta"]["requestId"].startswith("req_")
