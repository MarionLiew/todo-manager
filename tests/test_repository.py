"""Tests for the todo-manager repository data layer."""
from __future__ import annotations

import sqlite3

import pytest

from todo_manager.store.repository import Store, connect


@pytest.fixture()
def store(tmp_path) -> Store:
    conn = connect(str(tmp_path / "test.db"))
    return Store(conn)


def test_schema_initializes(store: Store) -> None:
    tables = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = {t["name"] for t in tables}
    assert {"tasks", "projects", "task_project", "task_context", "audit"} <= names


def test_add_task_creates_with_fields(store: Store) -> None:
    task = store.add_task(
        "订酒店", notes="可免费取消", priority="high", due="2026-09-28",
        contexts=["生活", "收集"], project_id=None,
    )
    assert task["title"] == "订酒店"
    assert task["status"] == "open"
    assert task["priority"] == "high"
    assert task["due"] == "2026-09-28"
    assert set(task["contexts"]) == {"生活", "收集"}


def test_add_task_dry_run_does_not_write(store: Store) -> None:
    result = store.add_task("不落库", dry_run=True)
    assert result["dry_run"] is True
    assert store.list_tasks() == []


def test_add_task_rejects_bad_context(store: Store) -> None:
    with pytest.raises(ValueError):
        store.add_task("x", contexts=["不存在的列表"])


def test_list_tasks_filters_status(store: Store) -> None:
    store.add_task("a", contexts=["工作"])
    store.add_task("b", contexts=["生活"])
    assert len(store.list_tasks(status="open")) == 2


def test_task_project_link(store: Store) -> None:
    project = store.add_project("9月需求", outcome="工单闭环")
    task = store.add_task("审核在线表", project_id=project["id"], contexts=["工作"])
    assert task["projects"] == [project["id"]]


def test_audit_recorded(store: Store) -> None:
    task = store.add_task("审计条目", contexts=["工作"])
    rows = store.conn.execute(
        "SELECT action,entity,entity_id FROM audit WHERE entity='task' AND entity_id=?",
        (task["id"],),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["action"] == "create"


def test_foreign_key_enforced(store: Store) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        store.conn.execute(
            "INSERT INTO task_project (task_id, project_id) VALUES (?,?)",
            ("nope", "nope"),
        )
        store.conn.commit()