"""Service tests for todo-os FastAPI app (local + tailnet-bound server)."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from todo_os.service.app import create_app

API_KEY = "test-key-123"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("TODO_OS_API_KEY", API_KEY)
    db = tmp_path / "todo.db"
    app = create_app(str(db))
    return TestClient(app)


def test_health_public(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_tasks_require_auth(client: TestClient) -> None:
    resp = client.get("/api/tasks")
    assert resp.status_code == 401


def test_add_task_with_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/tasks",
        json={"title": "订酒店", "priority": "high", "contexts": ["生活"]},
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "订酒店"
    assert data["priority"] == "high"
    assert set(data["contexts"]) == {"生活"}


def test_add_task_dry_run_no_write(client: TestClient) -> None:
    resp = client.post(
        "/api/tasks",
        json={"title": "不落库", "dry_run": True},
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["dry_run"] is True
    resp2 = client.get(
        "/api/tasks", headers={"Authorization": f"Bearer {API_KEY}"}
    )
    assert resp2.json()["data"] == []