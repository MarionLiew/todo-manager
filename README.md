# todo-manager

Local-first personal todo/project database with a data layer, a Tailnet-bound
HTTP service (kicked off later), and an Apple Reminders sync driver.

## Layout
- `todo_manager/store/` — SQLite data layer (schema, migrations, repository)
- `todo_manager/service/` — FastAPI service (later)
- `todo_manager/sync/reminders.py` — Reminders one-way push driver (later)

## Data model (GTD shapes as data, not hardcoded)
- tasks: id, title, notes, status, priority, due, created/updated/completed
- projects: outcome + next_action
- task <-> project links
- contexts as labels: 收集/工作/生活/投资/学习/等待/将来也许
- audit trail on every mutation

## Principles
- local-first; single SQLite source of truth
- mutations go through the repository with a dry-run/confirm gate
- TDD; run tests before delivery
- never put private data in git