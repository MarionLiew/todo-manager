#!/bin/bash
# todo-manager — one-time remote deploy script (self-contained).
#
# Run ONCE on any Hermes device that should reach the host's todo-manager
# service over Tailnet. Self-contained: if the full repo isn't on disk it
# clones it, then builds the venv and writes the connection config. Ships
# alongside SKILL.md (hermes skills install delivers both).
#
# Usage:
#   bash install-remote.sh --url http://100.105.74.36:8788 --key <KEY>
set -euo pipefail

URL=""
KEY=""
HERMES_SKILLS="${HERMES_SKILLS:-$HOME/.hermes/skills}"
REPO_DIR="$HOME/todo-manager"
GIT_REPO="https://github.com/MarionLiew/todo-manager.git"

usage() { echo "usage: $0 --url <server-url> --key <api-key>"; exit 1; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) URL="$2"; shift 2 ;;
    --key) KEY="$2"; shift 2 ;;
    *) usage ;;
  esac
done
[[ -n "$URL" && -n "$KEY" ]] || usage

# 1. Ensure the full repo (with todo_manager Python package) is on disk.
if [ ! -f "$REPO_DIR/pyproject.toml" ]; then
  echo "==> cloning todo-manager repo into $REPO_DIR"
  git clone "$GIT_REPO" "$REPO_DIR"
else
  echo "==> repo already present at $REPO_DIR"
fi
cd "$REPO_DIR"

# 2. Copy the skill (SKILL.md + scripts) into Hermes skills.
SKILL_DEST="$HERMES_SKILLS/todo-manager"
mkdir -p "$HERMES_SKILLS"
rm -rf "$SKILL_DEST"
mkdir -p "$SKILL_DEST/scripts"
cp "$REPO_DIR/SKILL.md" "$SKILL_DEST/"
cp "$REPO_DIR/scripts/install-remote.sh" "$SKILL_DEST/scripts/"
echo "==> skill files under $SKILL_DEST"

# 3. Python package + venv.
if command -v uv >/dev/null 2>&1; then
  uv sync --no-progress
  BIN="uv run todo-manager"
else
  python3 -m venv .venv
  ./.venv/bin/pip install -q -e .
  BIN=".venv/bin/todo-manager"
fi
echo "==> package ready ($BIN)"

# 4. Connection config (client role).
mkdir -p "$HOME/.todo-manager"
printf 'TODO_MANAGER_URL=%s\nTODO_MANAGER_API_KEY=%s\n' "$URL" "$KEY" > "$HOME/.todo-manager/.env"
chmod 600 "$HOME/.todo-manager/.env"
echo "==> wrote $HOME/.todo-manager/.env (client role)"

echo
echo "DONE. Verify:"
echo "  cd $REPO_DIR && $BIN role                # expect 'role=client'"
echo "  cd $REPO_DIR && $BIN sync remote health  # expect {\"status\":\"ok\"}"
echo "  cd $REPO_DIR && $BIN sync remote list    # host's tasks"
echo
echo "Keep $HOME/.todo-manager/.env private."