#!/usr/bin/env python3
"""dictation_ctl.py start|stop|quit — send a control message to the running
dictation app over its Unix socket. Meant to be bound to a GNOME keyboard
shortcut (Wayland blocks apps from registering their own global hotkeys, so
the key binding itself lives outside this app, in GNOME Settings).
"""
import socket
import subprocess
import sys
import time
from pathlib import Path

from config import CONFIG_DIR

SOCKET_PATH = CONFIG_DIR / "ctl.sock"
LAUNCHER = Path(__file__).resolve().parent / "dictation"
LAUNCH_TIMEOUT_SECONDS = 5


def send(action: str) -> bool:
    """Returns True if the message was delivered."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(SOCKET_PATH))
            sock.sendall(action.encode())
        return True
    except OSError:
        return False


def wait_for_socket(timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if SOCKET_PATH.exists():
            return True
        time.sleep(0.1)
    return False


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("start", "stop", "quit"):
        print("usage: dictation_ctl.py start|stop|quit", file=sys.stderr)
        return 1
    action = sys.argv[1]

    if send(action):
        return 0

    if action != "start":
        # Nothing running to stop/quit — not an error.
        return 0

    subprocess.run([str(LAUNCHER), "start"], check=True)
    if not wait_for_socket(LAUNCH_TIMEOUT_SECONDS):
        print("dictation app didn't come up in time", file=sys.stderr)
        return 1
    if not send(action):
        print("dictation app started but the control socket didn't respond", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
