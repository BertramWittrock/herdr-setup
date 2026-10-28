"""Light F1-F10 on the Razer keyboard with the status of agent 1-10 in the herdr sidebar.

Listens to herdr's event socket, so keys change the moment an agent's status does.
Holding Shift switches the F-keys to the Shift+F shortcuts from config.toml instead.
Runs at login via ~/Library/LaunchAgents/dk.celto.herdr-keylights.plist.
"""
import ctypes
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RAZER_KEYS = os.path.join(HERE, "razer-keys")
JUMP = os.path.expanduser("~/.config/herdr/jump.sh")
SPACE_FILTER = os.path.expanduser("~/.config/herdr/space-filter.py")
SPACE_ONLY_STATE = os.path.join(
    os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")), "herdr", "agents-current-space"
)
SOCKET = os.path.expanduser("~/.config/herdr/herdr.sock")

# Colours as RRGGBB. Status colours follow herdr's sidebar dots.
BASE = "303030"  # every other key (dim white)
EMPTY = "000000"  # F-key with no agent behind it
STATUS = {
    "blocked": "ff0000",  # input needed
    "working": "ffb000",
    "done": "00c8c8",
    "idle": "00ff00",
    "unknown": "505050",
}

# Shown while Shift is held: F-key number -> colour, matching the Shift+F bindings in config.toml.
# Shift+F1-F6 light when that workspace exists; other F-keys not listed go dark.
WORKSPACE = "00ff00"  # Shift+F1-F6: jump to workspace 1-6 (green)
WORKSPACE_KEYS = 6
SHIFT_LAYER = {
    7: "ff4000",  # Shift+F7: new Claude Code tab (orange)
    8: "8000ff",  # Shift+F8: new Command Code tab (purple)
    9: "ffffff",  # Shift+F9: new opencode tab (white)
    10: "0050ff",  # Shift+F10: new Codex tab (blue)
    12: BASE,  # Shift+F12: close pane (left like the rest of the keyboard)
}
SPACE_ONLY_ON = "ffffff"  # F11 when Shift+F11's "this space only" agent list is on (white; dim when off)
SHIFT_HOLD_SECONDS = 0  # raise (e.g. 0.2) if typing capitals flashing the layer gets distracting
SHIFT_POLL_SECONDS = 0.01

ROWS, COLS = 6, 22
F1_COL = 3  # F1-F12 sit in row 0, columns 3-14
F_KEYS = 10  # agent keys
ALL_F_KEYS = 12

LIFECYCLE_EVENTS = [
    "pane.created", "pane.closed", "pane.moved", "pane.exited", "pane.agent_detected",
    "tab.created", "tab.closed", "tab.moved",
    "workspace.created", "workspace.closed", "workspace.moved", "workspace.reordered",
    "workspace.focused",  # "this space only" shows a different set of agents per space
]
# New pane ids need their own status subscription, so these end the current one.
# (Pushed events use underscores: subscribe to "pane.created", receive "pane_created".)
NEW_PANE_EVENTS = {"pane_created", "pane_moved"}
FALLBACK_REFRESH_SECONDS = 5  # also catches sidebar sort toggles and keyboard replugs

last_frame = None
statuses = []
workspaces = set()  # workspace numbers that exist
space_only = False  # Shift+F11 mode, saved by space-filter.py
shift_layer = False
paint_lock = threading.RLock()  # the event loop and the Shift watcher both paint


def ordered_statuses():
    """Agent statuses in sidebar order, or [] when herdr is not reachable."""
    result = subprocess.run([JUMP, "agents"], capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return [line.split()[1] for line in result.stdout.splitlines() if len(line.split()) == 2]


def workspace_numbers():
    result = subprocess.run(["herdr", "workspace", "list"], capture_output=True, text=True)
    if result.returncode != 0:
        return set()
    return {workspace["number"] for workspace in json.loads(result.stdout)["result"]["workspaces"]}


def frame_for(statuses, workspaces, shift, space_only):
    frame = [[BASE] * COLS for _ in range(ROWS)]
    if shift:
        for i in range(ALL_F_KEYS):
            n = i + 1
            if n == 11:
                colour = SPACE_ONLY_ON if space_only else BASE
            else:
                colour = WORKSPACE if n <= WORKSPACE_KEYS and n in workspaces else EMPTY
            frame[0][F1_COL + i] = SHIFT_LAYER.get(n, colour)
        return "".join("".join(row) for row in frame)
    for i in range(F_KEYS):
        status = statuses[i] if i < len(statuses) else None
        frame[0][F1_COL + i] = STATUS.get(status, STATUS["unknown"]) if status else EMPTY
    frame[0][F1_COL + 10] = SPACE_ONLY_ON if space_only else BASE  # F11 shows the Shift+F11 mode
    return "".join("".join(row) for row in frame)


def paint(frame):
    global last_frame
    with paint_lock:
        if frame == last_frame:
            return
        ok = subprocess.run([RAZER_KEYS, frame], capture_output=True).returncode == 0
        last_frame = frame if ok else None  # retry next time if the keyboard was busy or unplugged


def render():
    paint(frame_for(statuses, workspaces, shift_layer, space_only))


def refresh():
    global statuses, workspaces, space_only
    statuses = ordered_statuses()
    workspaces = workspace_numbers()
    space_only = os.path.exists(SPACE_ONLY_STATE)
    render()


def watch_shift():
    """Show the Shift layer while Shift has been held for SHIFT_HOLD_SECONDS."""
    global shift_layer
    core_graphics = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
    core_graphics.CGEventSourceFlagsState.argtypes = [ctypes.c_int32]
    core_graphics.CGEventSourceFlagsState.restype = ctypes.c_uint64
    hid_system_state, shift_mask = 1, 0x20000
    held_since = None
    while True:
        held = bool(core_graphics.CGEventSourceFlagsState(hid_system_state) & shift_mask)
        held_since = (held_since or time.monotonic()) if held else None
        layer = held_since is not None and time.monotonic() - held_since >= SHIFT_HOLD_SECONDS
        if layer != shift_layer:
            shift_layer = layer
            render()
        time.sleep(SHIFT_POLL_SECONDS)


def pane_ids():
    result = subprocess.run(["herdr", "pane", "list"], capture_output=True, text=True)
    return [pane["pane_id"] for pane in json.loads(result.stdout)["result"]["panes"]]


def watch_once():
    """Subscribe, then refresh on every event until a new pane appears or herdr goes away."""
    subscriptions = [{"type": t} for t in LIFECYCLE_EVENTS]
    subscriptions += [{"type": "pane.agent_status_changed", "pane_id": p} for p in pane_ids()]
    with socket.socket(socket.AF_UNIX) as sock:
        sock.connect(SOCKET)
        request = {"id": "keylights", "method": "events.subscribe", "params": {"subscriptions": subscriptions}}
        sock.sendall((json.dumps(request) + "\n").encode())
        stream = sock.makefile()
        ack = json.loads(stream.readline() or "{}")
        if "error" in ack:
            raise ConnectionError(ack["error"])
        if os.path.exists(SPACE_ONLY_STATE):  # agent views are lost when herdr restarts
            subprocess.run([sys.executable, "-I", SPACE_FILTER, "apply"], capture_output=True)
        refresh()
        sock.settimeout(FALLBACK_REFRESH_SECONDS)
        while True:
            try:
                line = stream.readline()
            except TimeoutError:
                refresh()
                continue
            if not line:
                return  # server closed the subscription (restart or events_lost)
            refresh()
            if json.loads(line).get("event") in NEW_PANE_EVENTS:
                return


def stop(*_):
    paint(frame_for([], set(), False, False))
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    # space-filter.py sends SIGUSR1 after a toggle; refresh off the main thread, which may be mid-read.
    signal.signal(signal.SIGUSR1, lambda *_: threading.Thread(target=refresh).start())
    threading.Thread(target=watch_shift, daemon=True).start()
    while True:
        try:
            watch_once()
        except (OSError, ValueError, KeyError, ConnectionError):
            refresh()  # herdr down: F-keys go dark
            time.sleep(2)


if __name__ == "__main__":
    main()
