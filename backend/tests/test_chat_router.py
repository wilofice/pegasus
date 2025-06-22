from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_chat_missing_auth() -> None:
    resp = client.post("/chat/", json={"message": "hi"})
    assert resp.status_code == 401


def test_chat_ok(monkeypatch) -> None:
    monkeypatch.setattr("backend.core.orchestrator.handle_chat", lambda msg: "pong")
    resp = client.post("/chat/", json={"message": "ping"}, headers={"Authorization": "token"})
    assert resp.status_code == 200
    assert resp.json() == {"response": "pong"}
