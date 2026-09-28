#!/bin/bash
# todo-manager — one-time remote deploy script.
#
# Run ONCE on any Hermes device that should reach the host's todo-manager
# service over Tailnet. It:
#   1. copies the todo-manager skill into the local Hermes skills dir
#   2. creates a local venv and installs the package
#   3. writes ~/.todo-manager/.env with the host URL + the API key you passed
#
# Usage:
#   bash install-remote.sh --url http://100.105.74.36:8788 --key <KEY>
set -euo pipefail

URL=""
KEY=""
HERMES_SKILLS="${HERMES_SKILLS:-$HOME/.hermes/skills}"

usage() { echo "usage: $0 --url <server-url> --key <api-key>"; exit 1; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) URL="$2"; shift 2 ;;
    --key) KEY="$2"; shift 2 ;;
    *) usage ;;
  esac
done
[[ -n "$URL" && -n "$KEY" ]] || usage

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "==> source dir: $SRC"

# 1. Install as a Hermes skill (single copy).
SKILL_DEST="$HERMES_SKILLS/com.marion.todo-manager"
mkdir -p "$HERMES_SKILLS"
rm -rf "$SKILL_DEST"
cp -R "$SRC" "$SKILL_DEST"
echo "==> skill installed at $SKILL_DEST"

# 2. Local venv + package.
cd "$SRC"
if command -v uv >/dev/null 2>&1; then
  uv sync --dev --no-progress
  BIN="uv run todo-manager"
else
  python3 -m venv .venv
  ./.venv/bin/pip install -q -e . 2>/dev/null || ./.venv/bin/pip install -q .
  BIN=".venv/bin/todo-manager"
fi
echo "==> package ready ($BIN)"

# 3. Connection config.
mkdir -p "$HOME/.todo-manager"
printf 'TODO_MANAGER_URL=%s\nTODO_MANAGER_API_KEY=%s\n' "$URL" "$KEY" > "$HOME/.todo-manager/.env"
chmod 600 "$HOME/.todo-manager/.env"
echo "==> wrote $HOME/.todo-manager/.env"

echo
echo "DONE. Verify connectivity:"
echo "  $BIN sync remote health"
echo "  $BIN sync remote list"
echo
echo "Tip: add TODO_MANAGER_URL / TODO_MANAGER_API_KEY to your shell env, or source "$HOME/.todo-manager/.env"."