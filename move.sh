#!/bin/sh
# Move the current pane (and the agent in it) to workspace N, as a new tab that keeps its name.
# You stay in the workspace you're in. Usage: move.sh N
# Bound to ctrl+b then Shift+F1–F6 in config.toml via [[keys.command]].
set -eu

PATH="/opt/homebrew/bin:$PATH"
herdr="${HERDR_BIN_PATH:-herdr}"
n=$1

pane=${HERDR_ACTIVE_PANE_ID:-$("$herdr" pane list | jq -r '.result.panes[] | select(.focused) | .pane_id')}
target=$("$herdr" workspace list | jq -r --argjson n "$n" \
  '.result.workspaces[] | select(.number == $n) | .workspace_id')

# No workspace at that number, or the pane is already there: do nothing.
[ -n "$pane" ] && [ -n "$target" ] && [ "${pane%%:*}" != "$target" ] || exit 0

label=$("$herdr" pane get "$pane" | jq -r '.result.pane.tab_id' | xargs "$herdr" tab get | jq -r '.result.tab.label')
exec "$herdr" pane move "$pane" --workspace "$target" --new-tab --label "$label" --no-focus
