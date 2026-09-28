"""SQLite schema for todo-manager. Zero-dependency (stdlib sqlite3)."""
from __future__ import annotations

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    notes       TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open','done','deferred','cancelled')),
    priority    TEXT NOT NULL DEFAULT 'none'
                CHECK (priority IN ('none','low','medium','high')),
    due         TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    outcome     TEXT NOT NULL DEFAULT '',
    next_action_task_id TEXT REFERENCES tasks(id),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_project (
    task_id     TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, project_id)
);

CREATE TABLE IF NOT EXISTS task_context (
    task_id     TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    context     TEXT NOT NULL,
    PRIMARY KEY (task_id, context)
);

CREATE TABLE IF NOT EXISTS audit (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    action      TEXT NOT NULL,
    entity      TEXT NOT NULL,
    entity_id   TEXT NOT NULL,
    detail      TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit(entity, entity_id);
"""


def init_db(conn) -> None:
    conn.executescript(SCHEMA)
    conn.commit()