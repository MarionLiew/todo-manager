"""CLI entrypoint for todo-os: run the server locally or bound to a tailnet interface, and inspect the DB."""
from __future__ import annotations

import os
import sys

import click
import uvicorn

from todo_os.service.app import DEFAULT_DB, create_app


@click.group()
def cli() -> None:
    """todo-os: local-first personal todo/project database."""


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--port", default=8788, show_default=True, help="Bind port.")
@click.option("--db", default=DEFAULT_DB, show_default=True, help="SQLite path.")
def serve(host: str, port: int, db: str) -> None:
    """Run the todo-os HTTP service."""
    if not os.environ.get("TODO_OS_API_KEY"):
        click.echo("TODO_OS_API_KEY not set; refusing to start unauthenticated.", err=True)
        sys.exit(1)
    uvicorn.run(create_app(db), host=host, port=port, log_level="info")


@cli.command()
@click.option("--db", default=DEFAULT_DB, show_default=True)
def health(db: str) -> None:
    """Open the DB and confirm the schema is valid."""
    from todo_os.store.repository import Store, connect

    store = Store(connect(db))
    tables = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    click.echo(f"db={db}")
    click.echo(f"tables={', '.join(sorted(t['name'] for t in tables))}")


if __name__ == "__main__":
    cli()