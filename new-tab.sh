#!/bin/sh
# Open a new tab in the current workspace and folder, then start an agent in it.
# Usage: new-tab.sh COMMAND   (e.g. claude, cmd, opencode, codex)
# Bound to Shift+F7–F10 in config.toml via [[keys.command]].
set -eu

PATH="/opt/homebrew/bin:$PATH"
herdr="${HERDR_BIN_PATH:-herdr}"
agent=$1

set -- --cwd "${HERDR_ACTIVE_PANE_CWD:-$HOME}" --label "$agent" --focus
[ -n "${HERDR_ACTIVE_WORKSPACE_ID:-}" ] && set -- "$@" --workspace "$HERDR_ACTIVE_WORKSPACE_ID"

pane=$("$herdr" tab create "$@" | jq -r '.result.root_pane.pane_id')
exec "$herdr" pane run "$pane" "$agent"
