---
name: todo-manager
description: "Local-first personal todo/project database with a cross-device HTTP service. Owns the data layer (SQLite), an authenticated FastAPI service on Tailnet, and sync drivers (Apple Reminders push + remote client). Use whenever the user manages todos/projects, wants tasks to sync across Hermes sessions/devices, or needs a reminder or cross-machine todo."
version: 0.1.0
author: Marion Liew
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [todos, gtd, projects, sqlite, fastapi, sync, reminders, tailscale]
---

# todo-manager

Local-first personal todo/project database. Single SQLite source of truth, an
authenticated FastAPI service bound to Tailnet so any Hermes on any device can
read/write the same tasks, and Apple Reminders as a one-way notification
channel for time-sensitive items.

## Core principle

The SQLite DB is the single source of truth. Everything else (the HTTP
service, the remote client, Apple Reminders) is a view/interface over it. Never
let Reminders or a chat window become the source of truth for task state.

## Layout

- `todo_manager/store/` — SQLite schema (`schema.py`) + repository (`repository.py`). All mutations go through the repository with audit + `dry_run` gate. Contexts: 收集/工作/生活/投资/学习/等待/将来也许.
- `todo_manager/service/app.py` — FastAPI app, bearer-auth, `/health` public.
- `todo_manager/sync/reminders.py` — one-way push of tasks with a due date to Apple Reminders via `remindctl`.
- `todo_manager/sync/remote.py` — client for a remote todo-manager service (uses `TODO_MANAGER_URL` + `TODO_MANAGER_API_KEY` env).
- `todo_manager/cli.py` — `todo-manager` entrypoint.

## Run / manage

- **Service (this Mac, persisted via launchd `com.marion.todo-manager`):**
  ```bash
  launchctl kickstart -k gui/$(id -u)/com.marion.todo-manager   # restart
  curl -s http://127.0.0.1:8788/health                          # health
  ```
  Binds 0.0.0.0:8788 (reachable via Tailnet IP `100.105.74.36` and LAN IP).
  Reads API key from `~/.todo-manager/.env` (chmod 600, never in git).
- **Data dir:** `~/.todo-manager/` (`todo.db` + `.env`).
- **Local CLI:** `uv run todo-manager health --db ~/.todo-manager/todo.db`
- **Push time-sensitive tasks to Apple Reminders:**
  ```bash
  uv run todo-manager sync push-reminders --db ~/.todo-manager/todo.db            # preview
  uv run todo-manager sync push-reminders --db ~/.todo-manager/todo.db --apply     # push
  ```
  Dedup is by exact title; verify no near-duplicate reminder already exists
  before applying (same textual task created under slightly different titles
  will NOT be deduped).
- **As a remote client (a Hermes instance on another device):**
  ```bash
  export TODO_MANAGER_URL=http://100.105.74.36:8788
  export TODO_MANAGER_API_KEY=<from host ~/.todo-manager/.env>
  todo-manager sync remote health
  todo-manager sync remote list
  todo-manager sync remote add "任务标题" --context 工作 --due "2026-09-29 12:00"
  ```

## Adding a task

Same semantics locally and remotely:
```bash
# local
uv run python -c "
from todo_manager.store.repository import Store, connect
import os
s = Store(connect(os.path.expanduser('~/.todo-manager/todo.db')))
s.add_task('审计在线表', due='2026-09-28', priority='high', contexts=['工作'])
"
# remote
todo-manager sync remote add "审计在线表" --context 工作 --due "2026-09-28" --priority high
```

## Dev

```bash
uv sync --dev
uv run pytest            # 18 tests
uv run ruff check .
```

## Pitfalls

- Never commit `~/.todo-manager/.env`, `*.db`, or `.logs/` (all in `.gitignore`).
- Reminders dedup is exact-title only. Before `--apply`, manually check
  `remindctl search '<title>'` for a near-duplicate, otherwise you'll create
  two notifications for the same underlying task.
- launchd runs the service in foreground (uv run todo-manager serve); KeepAlive
  tracks the real PID. If `uv` isn't on PATH at `~/.local/bin/uv`, adjust the
  plist ProgramArguments.
- API key missing → service refuses to start (deliberate). Set it in
  `~/.todo-manager/.env` before starting.

## TODO (not yet built)

- `SKILL.md` cross-device install notes / distribution playbook for giving a
  Hermes on another device the `sync remote` client.