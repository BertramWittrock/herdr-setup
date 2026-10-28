# herdr setup — notes for next time

Context for picking this back up (set up with Claude Code, Oct 2026, herdr 0.9.3, Warp, macOS 15 on Apple Silicon).

`~/.config/herdr` is a git repo: [BertramWittrock/herdr-setup](https://github.com/BertramWittrock/herdr-setup) (public). Only the setup files are tracked; herdr's sessions, logs and sockets stay on each Mac. `~/HERDR.md` links to this file. Personal notes for a Mac go in `LOCAL.md` beside it, which is never committed.

## Install on another Mac

Needs an Apple Silicon Mac with [Homebrew](https://brew.sh).

```sh
herdr server stop 2>/dev/null; [ -d ~/.config/herdr ] && mv ~/.config/herdr ~/.config/herdr.old
git clone https://github.com/BertramWittrock/herdr-setup.git ~/.config/herdr
~/.config/herdr/install.sh
```

`install.sh` installs herdr, jq, Python and Warp if missing; builds the keyboard tool and starts the light watcher; creates the Warp tab and `~/Applications/Herdr.app`; hooks Claude, Codex and opencode into herdr; and lists any agent CLIs still to install. Plug in the keyboard and it lights up; no Razer software needed. Re-run it any time; it's safe to repeat.

Keep both Macs in sync: after changing something, `cd ~/.config/herdr && git commit -am "…" && git push`; on the other Mac, `git pull && ./install.sh`.

## Key map

| Keys | Does |
|---|---|
| F1–F10 | Jump to agent 1–10, in the sidebar's current order |
| Shift+F1–F6 | Jump to workspace 1–6 (meant for keyboard macro keys) |
| Shift+F7 / F8 / F9 / F10 | New tab running Claude Code / Command Code (`cmd`) / opencode / Codex |
| F12 | Rename current tab (built-in prompt; the sidebar shows the tab name) |
| Shift+F11 | Toggle "this space only": the agent list (and F1–F10) show just the current space, in fixed tab order. F11 lights white while on |
| Shift+F12 | Close current pane — no confirmation |
| ctrl+shift+arrows | Move between panes (`ctrl+b` + arrow also works) |
| Hold Shift | F1–F6 green for each workspace that exists; F7 orange, F8 purple, F9 white, F10 blue; F11 white while "this space only" is on; F12 dim white |

Typing `herdr` in Spotlight or Raycast opens a new Warp window running herdr.

## Files

| Path | What |
|---|---|
| `~/.config/herdr/config.toml` | Keybindings. Check with `herdr config check`, apply with `herdr server reload-config` (or `ctrl+b shift+r`) |
| `~/.config/herdr/jump.sh` | `agent N` / `workspace N` focus; `agents` prints `pane_id status` in sidebar order (used by keylights) |
| `~/.config/herdr/space-filter.py` | Shift+F11 toggle; sets/clears a herdr agent view. Mode saved as `~/.local/state/herdr/agents-current-space`; keylights re-applies it after herdr restarts |
| `~/.config/herdr/new-tab.sh` | New tab in the current workspace and folder, then runs the given agent command |
| `~/.config/herdr/keylights/` | Keyboard lighting: `keylights.py` (watcher), `razer-keys.c` + `build.sh` (USB tool on `librazermacos/`, a git submodule), `keylights.log` |
| `~/.config/herdr/install.sh` | Sets up a Mac; writes the three files below |
| `~/Library/LaunchAgents/dk.celto.herdr-keylights.plist` | Starts the watcher at login, restarts it if it dies (written by `install.sh`) |
| `~/Applications/Herdr.app` | Launcher; opens `warp://tab_config/herdr?new_window=true` (built by `install.sh`) |
| `~/.warp/tab_configs/herdr.toml` | Warp tab config that runs `herdr` (copied from `warp/herdr.toml` by `install.sh`) |

## Keyboard lighting

- F-keys show each agent's status, live, in the sidebar's colours: red = input needed, yellow = working, teal = done, green = idle, dark = no agent. Rest of the keyboard is dim white (`BASE`).
- Colours and Shift settings are constants at the top of `keylights.py`. After editing: `launchctl kickstart -k gui/$(id -u)/dk.celto.herdr-keylights`
- Stop: `launchctl bootout gui/$(id -u)/dk.celto.herdr-keylights` (delete the plist to stop it starting at login).
- Rebuild the USB tool: `~/.config/herdr/keylights/build.sh`
- How it works: subscribes to herdr's socket events (plus a 5 s fallback refresh). Shift state is polled every 10 ms via `CGEventSourceFlagsState`; no macOS permission was needed. Latency is about 20–30 ms.
- Don't install Razer Synapse: there's no lighting API for other programs on Mac, it likely doesn't support this keyboard, and it would fight the watcher for the lights.

## Closing and restarting

- Closing the Warp window (or `ctrl+b q`) only detaches. The herdr server keeps running in the background with every pane and agent still working; opening Herdr again reattaches exactly as you left it.
- If the server stops (Mac restart, crash, `herdr server stop`): workspaces, tabs, names, splits and folders come back from `~/.config/herdr/session.json`. Claude, Codex and opencode resume their conversations automatically (`[session] resume_agents_on_restore`, on by default). Command Code, dev servers and other commands come back as empty shells in the right folder. Old screen contents only return with `[experimental] pane_history = true` (off: it saves terminal output, including secrets, to disk).
- Older layouts: `~/.config/herdr/session-snapshots/` (up to 48). Recovery steps are in herdr's docs, "Session state and restore".

## Things learned about herdr

- herdr has no separate "spaces" concept: in the UI, "spaces" means workspaces. The nesting is session → workspace → tab → pane; an agent is a process detected inside a pane.
- Built-in indexed actions (`focus_agent`, `switch_workspace`, `switch_tab`) only accept `<modifier>+1..9`, so the F-keys use `[[keys.command]]` with `type = "shell"` calling the scripts. Commands get `HERDR_BIN_PATH`, `HERDR_ACTIVE_WORKSPACE_ID`, `HERDR_ACTIVE_PANE_CWD`, etc.
- Test a config without touching the real one: `HERDR_CONFIG_PATH=/tmp/x.toml herdr config check`
- Sidebar agent rows are set in config.toml `[ui.sidebar.agents] rows` (now: agent name bold on top, then machine/workspace/tab). Tokens: state_icon, state_text, machine, workspace, tab, pane, agent, terminal_title(_stripped); style one with `{ token = "agent", bold = true, fg = "#RRGGBB", dim = false }`.
- The sort toggle is the label at the right end of the agent list header ("priority" / "grouped"). Clicking it saves a client preference that overrides config.toml.
- Agent views (`agent.view.set` on the socket) filter and sort the sidebar agent list and herdr's own indexed focus, but NOT `herdr agent list`, so `jump.sh` mirrors the filter itself. Views are lost when the herdr server exits. While a view is active, the header shows its label instead of the sort toggle.
- herdr doesn't pick up config.toml edits by itself: always run `herdr server reload-config` afterwards.
- The sidebar sort toggled in the UI is saved in `~/.local/state/herdr/client-shell/local-*.json` (`agent_panel_sort`), not in config.toml. It's currently `priority`.
- Priority order (copied from herdr 0.9.3 `src/client/shell/agent_sidebar.rs`): blocked > done > working > idle > unknown, then most recent state change first. If a herdr update changes this, update `ordered_agents` in `jump.sh`.
- Socket API: newline-delimited JSON on `~/.config/herdr/herdr.sock`. Subscriptions use dotted names (`pane.created`); pushed events arrive with underscores (`pane_created`). `pane.agent_status_changed` needs a `pane_id` per pane, and the whole subscribe call fails if any listed pane no longer exists.
- Logs: `~/.config/herdr/herdr-server.log` (API calls, not key presses) and `herdr-client.log`.
- Command Code (`npm i -g command-code`, binary `cmd`, logged in as BertramWittrock) reports its own status to herdr; no integration needed. It's installed under nvm Node 22.21.1, so reinstall it if you switch Node versions.
- Codex (`codex`, also under nvm Node 22.21.1) has herdr's codex integration installed, so its status shows like the others.

## Machine quirks

- Keyboard: Razer BlackWidow Chroma V2 (USB 0x1532:0x0221), lighting grid 6 rows × 22 columns, F1–F12 in row 0, columns 3–14. Has 5 macro keys (M1–M5), not 6.
- Rectangle owns `ctrl+option+arrows`. macOS uses `ctrl+arrows` for switching desktops.
- macOS "Use F1, F2… as standard function keys" is off (only matters for the Apple keyboard).
- Danish layout: avoid Option-based shortcuts, since Option types characters like @ { }.

## Open ideas / not done

- Teal ("done") and green ("idle") look alike on this keyboard; consider blue for done.
- Macro keys M1–M5 aren't wired up yet: unknown what they send without Razer software (test with `cat -v`). The Shift+F1–F6 workspace keys are ready for them.
- Shift layer could light Shift+F12 (close pane) red.
