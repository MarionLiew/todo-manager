"""Remote client for todo-manager — used by Hermes on ANOTHER device to reach
this machine's service over Tailnet and reuse the same storage/CLI semantics.

The remote talks plain HTTPS-or-HTTP to the service URL and lets the host do
all writes through its repository (single source of truth). Run the same CLI
as local (add / list) — this client just points at the service instead of a
local SQLite file.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from todo_manager.store.repository import VALID_CONTEXTS, VALID_PRIORITY


class RemoteError(RuntimeError):
    pass


def _base_url() -> str:
    url = os.environ.get("TODO_MANAGER_URL")
    if not url:
        raise RemoteError("TODO_MANAGER_URL not set (e.g. http://100.105.74.36:8788)")
    return url.rstrip("/")


def _key() -> str:
    key = os.environ.get("TODO_MANAGER_API_KEY")
    if not key:
        raise RemoteError("TODO_MANAGER_API_KEY not set")
    return key


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_key()}"}


def health() -> dict[str, Any]:
    try:
        resp = httpx.get(f"{_base_url()}/health", timeout=8)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        raise RemoteError(f"health check failed: {e}") from e


def list_tasks(status: str | None = None) -> list[dict[str, Any]]:
    try:
        resp = httpx.get(
            f"{_base_url()}/api/tasks",
            headers=_headers(),
            params={"status": status} if status else None,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            raise RemoteError(str(data))
        return data["data"]
    except httpx.HTTPError as e:
        raise RemoteError(f"list failed: {e}") from e


def add_task(
    title: str,
    *,
    notes: str = "",
    priority: str = "none",
    due: str | None = None,
    contexts: list[str] | None = None,
    project_id: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    if priority not in VALID_PRIORITY:
        raise ValueError(f"invalid priority: {priority}")
    for c in contexts or []:
        if c not in VALID_CONTEXTS:
            raise ValueError(f"invalid context: {c}")
    payload = {
        "title": title,
        "notes": notes,
        "priority": priority,
        "due": due,
        "contexts": contexts or [],
        "project_id": project_id,
        "dry_run": dry_run,
    }
    try:
        resp = httpx.post(
            f"{_base_url()}/api/tasks",
            headers=_headers(),
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            raise RemoteError(str(data))
        return data["data"]
    except httpx.HTTPError as e:
        raise RemoteError(f"add failed: {e}") from e