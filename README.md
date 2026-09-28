# todo-manager

Local-first personal todo/project database — packaged as a Hermes skill.
One SQLite source of truth, an authenticated FastAPI service bound to Tailnet so
any Hermes on any device reads/writes the same tasks, and Apple Reminders as a
one-way notification channel for time-sensitive items.

**单仓库 = skill。** `SKILL.md` 是这个项目的入口文档；任何 Hermes 装了它，
既能当服务端（持有数据库的机器）也能当客户端（通过 Tailnet 连主机），
身份由 `~/.todo-manager/.env` 决定（`role` 命令可查）。

## Install on another Hermes device (one command)

```bash
hermes skills install https://raw.githubusercontent.com/MarionLiew/todo-manager/main/SKILL.md --name todo-manager
```

`hermes skills install` only copies `SKILL.md`. To become a working client, follow the
natural-language recipe under **"Becoming a client"** in `SKILL.md` (clone → `uv sync` →
write `~/.todo-manager/.env` with host URL + API key → verify with `role` / `sync remote health`).
One-shot automation: `bash scripts/install-remote.sh --url http://100.105.74.36:8788 --key <KEY>`.

## Layout

- `SKILL.md` — entry doc; deployment recipe + command map
- `todo_manager/store/` — SQLite data layer (schema, repository, audit, dry-run)
- `todo_manager/service/` — FastAPI service (bearer auth, binds 0.0.0.0:8788)
- `todo_manager/sync/reminders.py` — Apple Reminders one-way push
- `todo_manager/sync/remote.py` — remote client (uses `TODO_MANAGER_URL`/`TODO_MANAGER_API_KEY`)
- `todo_manager/cli.py` — `todo-manager` CLI (serve / health / role / sync …)
- `scripts/install-remote.sh` — one-shot remote deploy

## Data model (GTD shapes as data)

- tasks: id, title, notes, status(open/done/deferred/cancelled), priority, due, created/updated/completed
- projects: outcome + next_action; task↔project links; contexts as labels (收集/工作/生活/投资/学习/等待/将来也许); audit trail on every mutation

## Principles

- local-first; single SQLite source of truth (data dir `~/.todo-manager/`)
- mutations go through the repository with a dry-run/confirm gate
- TDD; run `uv run pytest` (18 tests) + `uv run ruff check .` before delivery
- never put private data in git (`.env`, `*.db`, `.logs/` all ignored)

MIT © 2026 Marion Liew.