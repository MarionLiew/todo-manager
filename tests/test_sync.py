"""Tests for the todo-manager sync drivers (reminders push + remote client)."""
from __future__ import annotations

from pathlib import Path

import pytest

from todo_manager.store.repository import Store, connect
from todo_manager.sync import reminders as rmod


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    conn = connect(str(tmp_path / "test.db"))
    return Store(conn)


@pytest.fixture()
def fake_remindctl(tmp_path: Path, monkeypatch) -> Path:
    """Install a fake remindctl that logs invocations to a file."""
    log = tmp_path / "calls.txt"
    script = tmp_path / "remindctl"
    script.write_text(
        "#!/bin/bash\n"
        f'echo "$*" >> {log}\n'
        'if [ "$1" = "search" ]; then echo ""; fi\n'
        'exit 0\n'
    )
    script.chmod(0o755)
    monkeypatch.setattr(rmod, "_remindctl", lambda: str(script))
    return log


def test_push_dry_run_no_write(store: Store, tmp_path: Path) -> None:
    store.add_task("带截止的任务", due="2026-09-28", contexts=["工作"])
    store.add_task("无截止不推", contexts=["生活"])
    planned = rmod.push_tasks(store, dry_run=True)
    assert len(planned) == 1
    assert planned[0]["would_push"] is True
    # nothing touched remindctl
    assert not (tmp_path / "calls.txt").exists()


def test_push_apply_calls_remindctl(store: Store, fake_remindctl: Path, tmp_path: Path) -> None:
    store.add_task("候补票", due="2026-09-29 12:00", priority="high", contexts=["生活"])
    planned = rmod.push_tasks(store, dry_run=False, list_name="生活")
    assert planned[0]["pushed"] is True
    calls = (tmp_path / "calls.txt").read_text()
    assert "--title" in calls and "候补票" in calls
    assert "--due" in calls and "2026-09-29 12:00" in calls
    assert "生活" in calls


def test_push_skips_task_already_in_reminders(store: Store, tmp_path: Path, monkeypatch) -> None:
    store.add_task("已存在的提醒", due="2026-09-28", contexts=["工作"])
    # simulate remindctl already having this title: search returns non-empty
    script = tmp_path / "remindctl_exists"
    script.write_text(
        "#!/bin/bash\n"
        'if [ "$1" = "search" ]; then echo "EXISTING-MATCH"; fi\n'
        'exit 0\n'
    )
    script.chmod(0o755)
    monkeypatch.setattr(rmod, "_remindctl", lambda: str(script))
    planned = rmod.push_tasks(store, dry_run=False)
    assert planned[0]["skipped_duplicate"] is True


def _patch_remote(monkeypatch, data_api):
    import httpx

    class FakeClient:
        def __init__(self):
            pass

        def get(self, url, headers=None, params=None, timeout=None):
            if url.endswith("/health"):
                return _Resp(200, {"status": "ok"})
            if url.endswith("/api/tasks"):
                return _Resp(200, {"status": "success", "data": data_api})
            return _Resp(404, {})

        def post(self, url, headers=None, json=None, timeout=None):
            return _Resp(200, {"status": "success", "data": {"dry_run": True, "title": json["title"]}})

    monkeypatch.setattr(httpx, "get", FakeClient().get)
    monkeypatch.setattr(httpx, "post", FakeClient().post)


class _Resp:
    def __init__(self, code, data):
        self.status_code = code
        self._data = data

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError("err", request=httpx.Request("GET", url=""), response=self)

    def json(self):
        return self._data


@pytest.fixture()
def remote_env(monkeypatch):
    monkeypatch.setenv("TODO_MANAGER_URL", "http://100.105.74.36:8788")
    monkeypatch.setenv("TODO_MANAGER_API_KEY", "k")


def test_remote_health(monkeypatch, remote_env) -> None:
    _patch_remote(monkeypatch, [])
    from todo_manager.sync.remote import health

    assert health()["status"] == "ok"


def test_remote_list(monkeypatch, remote_env) -> None:
    _patch_remote(monkeypatch, [{"title": "远端任务", "status": "open", "due": None}])
    from todo_manager.sync.remote import list_tasks

    tasks = list_tasks()
    assert tasks[0]["title"] == "远端任务"


def test_remote_add_validates_local(remote_env) -> None:
    """Context/priority validation is local to the client — matches the store."""
    from todo_manager.sync.remote import add_task

    with pytest.raises(ValueError):
        add_task("x", contexts=["不存在的列表"])
    with pytest.raises(ValueError):
        add_task("x", priority="urgent")