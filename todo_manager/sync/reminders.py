"""One-way push of time-sensitive todo-manager tasks to Apple Reminders.

Uses remindctl (the same CLI the apple-gtd skill relies on). The data layer
stays the single source of truth; Apple Reminders is only a notification
channel for tasks that have a due date.

Rules:
- Only tasks with a `due` and status 'open' are pushed.
- Existing same-titled reminders in the target list are not duplicated
  (search by title first).
- Dry-run lists what WOULD be pushed without touching Reminders.
"""
from __future__ import annotations

import shutil
import subprocess

from todo_manager.store.repository import Store

OUTPUT_FORMAT = "{title}\t{context}\t{due}"


class ReminderUnavailableError(RuntimeError):
    """remindctl missing or not authorized."""


def _remindctl() -> str:
    for cand in ("/opt/homebrew/bin/remindctl", "remindctl"):
        path = shutil.which(cand) or (cand if cand.startswith("/") else None)
        if path:
            return path
    raise ReminderUnavailableError("remindctl not found")


def _run(args: list[str]) -> str:
    proc = subprocess.run(
        [_remindctl(), *args],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if proc.returncode != 0:
        raise ReminderUnavailableError(proc.stderr.strip() or "remindctl failed")
    return proc.stdout


def _title_exists(title: str, list_name: str) -> bool:
    try:
        out = _run(["search", title, "--plain"])
    except ReminderUnavailableError:
        return False
    return bool(out.strip())


def push_tasks(store: Store, *, list_name: str = "收集", dry_run: bool = True) -> list[dict]:
    """Push open tasks that have a due date to the given Reminders list."""
    planned: list[dict] = []
    for task in store.list_tasks():
        if task["status"] != "open" or not task["due"]:
            continue
        ctx = ",".join(task["contexts"]) or "工作"
        if dry_run:
            planned.append({"title": task["title"], "ctx": ctx, "due": task["due"], "would_push": True})
            continue
        if _title_exists(task["title"], list_name):
            planned.append({"title": task["title"], "ctx": ctx, "due": task["due"], "skipped_duplicate": True})
            continue
        due = task["due"]
        _run(
            [
                "add",
                "--title",
                task["title"],
                "--list",
                list_name,
                "--due",
                due,
                "--alarm",
                due,
                "--priority",
                task["priority"],
                "--notes",
                task["notes"] or "",
                "--json",
            ]
        )
        planned.append({"title": task["title"], "ctx": ctx, "due": due, "pushed": True})
    return planned