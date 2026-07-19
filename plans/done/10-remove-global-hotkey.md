# Remove global hotkey entirely

**Status: done**

## Why

Step 4 ([done/09-step4-global-hotkey.md](done/09-step4-global-hotkey.md)) added `ControlSocket` + `hotkey_daemon.py`, and the underlying mechanism was verified working directly (sending `b"toggle"` over the Unix socket reliably triggered start/stop, checked via the app's real dbusmenu state). But binding it to a real key combo via GNOME Settings → Keyboard → Custom Shortcuts (`gsettings`) didn't actually fire the command when the user pressed it — a GNOME/environment integration issue outside this app's code, not something worth continuing to debug for a "nice to have" second way to trigger a feature that already works fine from the tray.

User's call: drop the whole feature rather than keep troubleshooting the GNOME keybinding layer. Same call as [done/08-remove-auto-output.md](done/08-remove-auto-output.md) — remove cleanly rather than leave a half-working feature around.

## Scope: everything

- `hotkey_daemon.py` — deleted.
- `main.py`:
  - Remove `ControlSocket` class entirely.
  - Remove `self.control_socket = ControlSocket(...)` / `.start()` from `App.__init__`.
  - Remove `self.control_socket.close()` from `App._on_quit`.
  - Remove the now-unused `socket`/`Path` imports and `SOCKET_PATH` constant if nothing else uses them.
- Tests: delete `tests/step4_global_hotkey/` (both files exist only to test `ControlSocket`/`hotkey_daemon.py`).
- Also reverted (done immediately, ahead of this plan): the GNOME custom keybinding itself, via `gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "[]"`.

## Docs
- `CLAUDE.md` project structure — remove the `hotkey_daemon.py` entry, drop `ControlSocket` from `main.py`'s description.
- `plans/01-implementation-steps.md` — mark Step 4 done-then-removed (same pattern as Step 2), pointing at this plan.
- `docs/general-context/00-general-plan.md` — the Unix-socket/hotkey design was central to a few sections there; add a note rather than rewriting the historical design, same treatment as the auto-type removal note.

## Not touched
- The tray click path (`TrayIcon`, `App._on_toggle`, `_toggle_worker`) — completely unaffected, that's still the only trigger now.

## Verification
- Full test suite green with no leftover references to `ControlSocket`/`hotkey_daemon`/`SOCKET_PATH`.
- Manual: run the app, confirm the tray click still starts/stops recording normally (nothing else regressed).
