"""Repository layer for todo-os. All mutations go through here with audit + dry-run gate."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from todo_os.store.schema import init_db

VALID_STATUS = {"open", "done", "deferred", "cancelled"}
VALID_PRIORITY = {"none", "low", "medium", "high"}
VALID_CONTEXTS = {"收集", "工作", "生活", "投资", "学习", "等待", "将来也许"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _utc() -> str:
    return _now()


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    init_db(conn)
    return conn


class Store:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    # ---------- tasks ----------
    def add_task(
        self,
        title: str,
        *,
        notes: str = "",
        priority: str = "none",
        due: str | None = None,
        contexts: list[str] | None = None,
        project_id: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        preview = {
            "action": "add_task",
            "title": title,
            "notes": notes,
            "priority": priority,
            "due": due,
            "contexts": contexts or [],
            "project_id": project_id,
        }
        if dry_run:
            return {"preview": preview, "dry_run": True}

        if priority not in VALID_PRIORITY:
            raise ValueError(f"invalid priority: {priority}")
        for c in contexts or []:
            if c not in VALID_CONTEXTS:
                raise ValueError(f"invalid context: {c}")

        task_id = str(uuid.uuid4())
        now = _utc()
        self.conn.execute(
            "INSERT INTO tasks (id,title,notes,status,priority,due,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (task_id, title, notes, "open", priority, due, now, now),
        )
        for c in set(contexts or []):
            self.conn.execute(
                "INSERT INTO task_context (task_id,context) VALUES (?,?)", (task_id, c)
            )
        if project_id:
            self.conn.execute(
                "INSERT INTO task_project (task_id,project_id) VALUES (?,?)",
                (task_id, project_id),
            )
        self._audit("create", "task", task_id, f"title={title}")
        self.conn.commit()
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            return None
        contexts = [
            r["context"]
            for r in self.conn.execute(
                "SELECT context FROM task_context WHERE task_id=?", (task_id,)
            )
        ]
        projects = [
            r["project_id"]
            for r in self.conn.execute(
                "SELECT project_id FROM task_project WHERE task_id=?", (task_id,)
            )
        ]
        d = dict(row)
        d["contexts"] = contexts
        d["projects"] = projects
        return d

    def list_tasks(self, *, status: str | None = None) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT id FROM tasks").fetchall()
        return [self.get_task(r["id"]) for r in rows]

    # ---------- audit ----------
    def _audit(self, action: str, entity: str, entity_id: str, detail: str = "") -> None:
        self.conn.execute(
            "INSERT INTO audit (action,entity,entity_id,detail,created_at) VALUES (?,?,?,?,?)",
            (action, entity, entity_id, detail, _utc()),
        )

    # ---------- projects ----------
    def add_project(
        self, name: str, *, outcome: str = "", dry_run: bool = False
    ) -> dict[str, Any]:
        preview = {"action": "add_project", "name": name, "outcome": outcome}
        if dry_run:
            return {"preview": preview, "dry_run": True}
        project_id = str(uuid.uuid4())
        now = _utc()
        self.conn.execute(
            "INSERT INTO projects (id,name,outcome,created_at,updated_at) VALUES (?,?,?,?,?)",
            (project_id, name, outcome, now, now),
        )
        self._audit("create", "project", project_id, f"name={name}")
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM projects WHERE id=?", (project_id,)
        ).fetchone()
        return dict(row)