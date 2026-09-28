"""Sync drivers for todo-manager.

- reminders: push time-sensitive tasks to Apple Reminders (one-way, via remindctl).
- remote: client used by a Hermes instance on another device to reach the
  todo-manager service over Tailnet. Shares the storage schema/CLI semantics.
"""