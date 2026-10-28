#!/bin/sh
# Focus the Nth agent or workspace, numbered the way the herdr sidebar shows them right now.
# Usage: jump.sh agent N | jump.sh workspace N
#        jump.sh agents    (print "pane_id status" per agent, in sidebar order)
# Bound to F-keys in config.toml via [[keys.command]]; keylights/ uses "agents".
set -eu

PATH="/opt/homebrew/bin:$PATH"
herdr="${HERDR_BIN_PATH:-herdr}"
kind=${1:-}
n=${2:-}

# Sidebar sort as toggled in the UI (saved per client), else config.toml, else "spaces".
sidebar_sort() {
  prefs=$(ls -t "${XDG_STATE_HOME:-$HOME/.local/state}"/herdr/client-shell/local-*.json 2>/dev/null | head -1)
  sort=$([ -n "$prefs" ] && jq -r '.agent_panel_sort // empty' "$prefs" 2>/dev/null || true)
  [ -n "$sort" ] || sort=$(sed -n 's/^agent_panel_sort *= *"\([a-z]*\)".*/\1/p' "$HOME/.config/herdr/config.toml" | head -1)
  echo "${sort:-spaces}"
}

# Same ordering as herdr's sidebar (src/client/shell/agent_sidebar.rs):
# priority = blocked > done > working > idle > unknown, newest state change first.
# With Shift+F11's "this space" view on (space-filter.py), only the current space, in tab then pane order.
ordered_agents() {
  if [ -f "${XDG_STATE_HOME:-$HOME/.local/state}/herdr/agents-current-space" ]; then
    jq -rn --argjson agents "$("$herdr" agent list)" --argjson tabs "$("$herdr" tab list)" \
      --argjson panes "$("$herdr" pane list)" --argjson spaces "$("$herdr" workspace list)" '
      ($spaces.result.workspaces[] | select(.focused) | .workspace_id) as $current
      | ($tabs.result.tabs | to_entries | map({(.value.tab_id): .key}) | add) as $tab_pos
      | ($panes.result.panes | to_entries | map({(.value.pane_id): .key}) | add) as $pane_pos
      | $agents.result.agents
      | map(select(.workspace_id == $current))
      | sort_by([$tab_pos[.tab_id], $pane_pos[.pane_id]])
      | .[] | "\(.pane_id) \(.agent_status)"'
    return
  fi
  "$herdr" agent list | jq -r --arg sort "$(sidebar_sort)" '
    {blocked: 4, done: 3, working: 2, idle: 1} as $rank
    | .result.agents
    | if $sort == "priority"
      then sort_by([-($rank[.agent_status] // 0), -(.state_change_seq // 0)])
      else . end
    | .[] | "\(.pane_id) \(.agent_status)"'
}

case $kind in
  agents)
    ordered_agents
    exit 0
    ;;
  agent)
    target=$(ordered_agents | sed -n "${n}p" | cut -d' ' -f1)
    ;;
  workspace)
    target=$("$herdr" workspace list | jq -r --argjson n "$n" \
      '.result.workspaces[] | select(.number == $n) | .workspace_id')
    ;;
  *)
    echo "usage: jump.sh agent|workspace N | jump.sh agents" >&2
    exit 2
    ;;
esac

# Nothing at that number: do nothing.
[ -n "$target" ] || exit 0
exec "$herdr" "$kind" focus "$target"
