"""Toggle showing only the current space's agents in the herdr sidebar (Shift+F11).

Uses herdr's agent view API: while on, the agent list shows the space you're in, in
tab then pane order, and follows you when you switch spaces. Views don't survive a
herdr restart, so keylights/keylights.py re-applies the saved mode when it reconnects.
jump.sh mirrors the same filter for F1-F10.
Usage: space-filter.py toggle | apply
"""
import json
import os
import socket
import subprocess
import sys

STATE = os.path.join(
    os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")), "herdr", "agents-current-space"
)
SOCKET = os.environ.get("HERDR_SOCKET_PATH", os.path.expanduser("~/.config/herdr/herdr.sock"))
SOURCE = "dk.celto.space-filter"
VIEW = {
    "source": SOURCE,
    "label": "this space",
    "filter": {"op": "eq", "field": "workspace_id", "value": {"context": "current_workspace_id"}},
    "sort": [{"field": "tab_order", "order": "asc"}, {"field": "pane_order", "order": "asc"}],
}


def request(method, params):
    with socket.socket(socket.AF_UNIX) as sock:
        sock.connect(SOCKET)
        sock.sendall((json.dumps({"id": "space-filter", "method": method, "params": params}) + "\n").encode())
        reply = json.loads(sock.makefile().readline())
    if "error" in reply:
        sys.exit(f"space-filter: {reply['error']}")


def apply():
    if os.path.exists(STATE):
        request("agent.view.set", VIEW)
    else:
        request("agent.view.clear", {"source": SOURCE})


def toggle():
    if os.path.exists(STATE):
        os.remove(STATE)
    else:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        open(STATE, "w").close()
    apply()
    # Repaint the key lights now instead of at their next 5 s refresh.
    subprocess.run(["launchctl", "kill", "SIGUSR1", f"gui/{os.getuid()}/dk.celto.herdr-keylights"], capture_output=True)


if __name__ == "__main__":
    {"toggle": toggle, "apply": apply}[sys.argv[1]]()
