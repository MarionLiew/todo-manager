"""FastAPI service exposing the todo-os store to local Hermes and remote devices over Tailnet."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class TaskIn(BaseModel):
    title: str
    notes: str = ""
    priority: str = "none"
    due: str | None = None
    contexts: list[str] | None = None
    project_id: str | None = None
    dry_run: bool = False

DEFAULT_DB = str(Path.home() / ".todo-os" / "todo.db")


def _api_key() -> str:
    return os.environ.get("TODO_OS_API_KEY", "")


def _db_path(override: str | None) -> str:
    path = override or DEFAULT_DB
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return path


def create_app(db_path: str | None = None) -> FastAPI:
    from todo_os.store.repository import Store, connect

    def store_dep():
        store = Store(connect(_db_path(db_path)))
        yield store
        store.conn.close()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def auth(request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        key = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not _api_key() or key != _api_key():
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/tasks")
    def list_tasks(status: str | None = None, store=Depends(store_dep)):  # noqa: B008
        return {"status": "success", "data": store.list_tasks(status=status)}

    @app.post("/api/tasks")
    def add_task(body: TaskIn, store=Depends(store_dep)):  # noqa: B008
        result = store.add_task(
            body.title,
            notes=body.notes,
            priority=body.priority,
            due=body.due,
            contexts=body.contexts,
            project_id=body.project_id,
            dry_run=body.dry_run,
        )
        return {"status": "success", "data": result}

    return app