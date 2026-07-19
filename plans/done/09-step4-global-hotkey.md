# Step 4 — Global hotkey

**Status: done**

Detailed plan for [Step 4](01-implementation-steps.md) of the overall build: a second way to trigger `controller.toggle()` — a keyboard shortcut — alongside the existing tray click. Same recording/popup/Copy-button behavior underneath; this step only adds a trigger.

## Why the socket, not a direct hotkey binding

Wayland (this session's compositor) blocks regular apps from registering global keyboard shortcuts directly — only the compositor itself can capture a hotkey and dispatch it. So:

1. The running app (`main.py`) listens on a Unix socket at `~/.config/dictation-tool/ctl.sock` for a `toggle` message.
2. A tiny standalone script, `hotkey_daemon.py`, connects to that socket and sends `toggle`, then exits.
3. The user binds *that script* to a key combo themselves via **GNOME Settings → Keyboard → Custom Shortcuts** (a native OS feature — can't be set programmatically, one-time manual step after this ships).

## Files

- **`main.py`** — add `ControlSocket`:
  - `__init__(on_toggle, socket_path=~/.config/dictation-tool/ctl.sock)`: creates the parent dir, removes a stale socket file left over from a previous crashed run (binding to an existing path otherwise fails), binds and listens.
  - `start()`: runs the accept loop on a background daemon thread — consistent with the rest of `main.py`'s existing background-thread + `GLib.idle_add` pattern, rather than wiring the socket fd into GLib's event loop directly (`GLib.io_add_watch`), which would be harder to test and isn't needed here — the accept loop already only does one thing (block on `accept()`, hand off through `idle_add`).
  - On receiving `b"toggle"`, calls `GLib.idle_add(self.on_toggle)` — same `_on_toggle` handler the tray click already uses, so there's no duplicated start/stop logic.
  - `close()`: closes the server socket and removes the socket file, called on quit.
  - `App.__init__` constructs and starts it; `App._on_quit` closes it before `Gtk.main_quit()`.
- **`hotkey_daemon.py`** (new, standalone script — not imported by the app): connects to the same socket path, sends `b"toggle"`, exits. Prints a stderr message and exits non-zero if the app isn't running (socket missing/connection refused) rather than raising a traceback, since this runs silently from a GNOME keybinding.

## Tests

New file `tests/step4_global_hotkey/test_control_socket.py`:
- `ControlSocket` bound to a temp path, started, a raw client socket connects and sends `b"toggle"` — assert the `on_toggle` callback fires (pumping `GLib.MainContext.default()` briefly since `idle_add` needs an iterating main loop to dispatch, no full `Gtk.main()` required for this).
- A second connection with unrecognized data (e.g. `b"garbage"`) — assert `on_toggle` does *not* fire.
- `close()` — assert the socket file is removed and a further connection attempt fails.

New file `tests/step4_global_hotkey/test_hotkey_daemon.py`:
- Start a raw listening socket at a temp path, run the daemon's `main()` against it, assert it received exactly `b"toggle"`.
- Point the daemon at a path with no listener — assert it exits cleanly (no unhandled exception), stderr has a message.

## Manual verification (needs a real desktop session)
1. Run `main.py`. In another terminal, run `python3 hotkey_daemon.py` — confirm recording starts (tray label flips, popup appears) exactly as a tray click would.
2. Run it again — confirm it stops the recording.
3. Bind `python3 /path/to/hotkey_daemon.py` to a key combo via GNOME Settings → Keyboard → Custom Shortcuts, confirm the real keypress triggers start/stop without touching the tray icon.
4. Quit the app, confirm the socket file at `~/.config/dictation-tool/ctl.sock` is removed (not left stale for the next launch).

## Dependencies
None new — `socket` and `threading` are stdlib.
