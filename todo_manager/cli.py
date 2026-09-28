"""CLI entrypoint for todo-manager: run the server locally or bound to a tailnet interface, and inspect the DB."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import click
import uvicorn

from todo_manager.service.app import DEFAULT_DB, create_app


@click.group()
def cli() -> None:
    """todo-manager: local-first personal todo/project database."""


def _load_env(db_dir: Path) -> None:
    env_file = db_dir / ".env"
    if env_file.is_file() and not os.environ.get("TODO_OS_API_KEY"):
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--port", default=8788, show_default=True, help="Bind port.")
@click.option("--db", default=DEFAULT_DB, show_default=True, help="SQLite path.")
def serve(host: str, port: int, db: str) -> None:
    """Run the todo-manager HTTP service."""
    _load_env(Path(db).parent)
    if not os.environ.get("TODO_OS_API_KEY"):
        click.echo("TODO_OS_API_KEY not set; refusing to start unauthenticated.", err=True)
        sys.exit(1)
    uvicorn.run(create_app(db), host=host, port=port, log_level="info")


@cli.command()
@click.option("--db", default=DEFAULT_DB, show_default=True)
def health(db: str) -> None:
    """Open the DB and confirm the schema is valid."""
    from todo_manager.store.repository import Store, connect

    store = Store(connect(db))
    tables = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    click.echo(f"db={db}")
    click.echo(f"tables={', '.join(sorted(t['name'] for t in tables))}")


@click.group()
def sync() -> None:
    """Sync drivers: push to Apple Reminders, or act as a remote client."""


@sync.command("push-reminders")
@click.option("--db", default=DEFAULT_DB, show_default=True)
@click.option("--list", "list_name", default="收集", show_default=True)
@click.option(
    "--apply",
    is_flag=True,
    default=False,
    help="Actually push; without it, only preview what would be pushed.",
)
def push_reminders(db: str, list_name: str, apply: bool) -> None:
    """Push open tasks with a due date to an Apple Reminders list (one-way)."""
    from todo_manager.store.repository import Store, connect
    from todo_manager.sync.reminders import push_tasks as push_reminders_impl

    store = Store(connect(db))
    planned = push_reminders_impl(store, list_name=list_name, dry_run=not apply)
    for row in planned:
        state = (
            "WOULD-PUSH"
            if row.get("would_push")
            else ("DUPLICATE" if row.get("skipped_duplicate") else "PUSHED")
        )
        click.echo(f"[{state}] {row['title']} — {row['ctx']} — {row['due']}")
    click.echo(f"({len(planned)} tasks {'would be' if not apply else ''} pushed)")


@sync.group()
def remote() -> None:
    """Talk to a remote todo-manager service (other device over Tailnet)."""


cli.add_command(sync)


@remote.command("health")
def remote_health() -> None:
    """Check the remote service is reachable and authenticated."""
    from todo_manager.sync.remote import health as r_health

    click.echo(r_health())


@remote.command("list")
def remote_list() -> None:
    """List tasks on the remote service."""
    from todo_manager.sync.remote import list_tasks

    for task in list_tasks():
        click.echo(f"- {task['title']} [{task['status']}] {task.get('due') or ''}")


@remote.command("add")
@click.argument("title")
@click.option("--notes", default="")
@click.option("--priority", default="none")
@click.option("--due")
@click.option("--context", "contexts", multiple=True)
@click.option("--dry-run", is_flag=True, default=False)
def remote_add(
    title: str,
    notes: str,
    priority: str,
    due: str | None,
    contexts: tuple[str, ...],
    dry_run: bool,
) -> None:
    """Add a task on the remote service."""
    from todo_manager.sync.remote import add_task

    result = add_task(
        title,
        notes=notes,
        priority=priority,
        due=due,
        contexts=list(contexts) or None,
        dry_run=dry_run,
    )
    click.echo(result)


if __name__ == "__main__":
    cli()