from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_webhook_bad_token() -> None:
    resp = client.post("/webhook/", json={"file_path": "a"})
    assert resp.status_code == 401


def test_webhook_ok(monkeypatch) -> None:
    called = {}
    def fake_process(payload):
        called['ok'] = payload
    monkeypatch.setattr("backend.core.proactive_engine.process_notification", fake_process)
    resp = client.post("/webhook/", json={"file_path": "f"}, headers={"X-Token": "pipeline-secret"})
    assert resp.status_code == 200
    assert called['ok'] == {"file_path": "f"}
