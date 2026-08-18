# Global shortcuts to control dictation (start/raise, stop, quit)

**Status: done**

## Why

Today the only way to use the tool is: open a terminal, run `dictation start`,
wait for the window, then click Start. If the window gets buried behind other
windows (common — the user works with many), there's no fast way back to it.

Three keyboard shortcuts are wanted:
1. **Start** — if the app isn't running, launch it and start recording. If it
   is running, bring the transcript window to the front (and start recording
   if it wasn't already recording).
2. **Stop** — stop the current recording, but leave the app running.
3. **Quit** — stop the app completely.

This was already attempted once and removed: [done/09-step4-global-hotkey.md](done/09-step4-global-hotkey.md)
built a `ControlSocket` + a script that sent a `toggle` message over a Unix
socket — verified working when triggered directly. It was ripped out
([done/10-remove-global-hotkey.md](done/10-remove-global-hotkey.md)) because
binding that script to a real key combo via GNOME Settings → Keyboard →
Custom Shortcuts never actually fired it.

Research (this machine: GNOME 46 on Wayland) points at a specific, fixable
cause rather than a dead end:

- Wayland blocks apps from registering their own global hotkeys — GNOME's
  Settings → Keyboard → Custom Shortcuts panel is the correct (and basically
  only) supported path here. X11 tools (`xbindkeys`/`sxhkd`/`xdotool`) are
  unreliable/non-functional under Wayland.
- GNOME's custom-keybinding schema is *relocatable* — every `gsettings set`
  on it must include the `:/org/.../custom-keybindings/customN/` path
  suffix, or the write silently goes nowhere while the Settings UI still
  looks correct. This matches "looked right, didn't fire" and is a
  well-documented gotcha.

So this reuses the previously-proven `ControlSocket` mechanism, but sets up
the GNOME keybindings with the correct relocatable-schema syntax, and has a
"verify with `notify-send` first" step so a binding failure and a script
failure can't be confused with each other again.

## Design

**App side** — resurrect `ControlSocket` in `main.py`, listening on a Unix
socket at `CONFIG_DIR / "ctl.sock"` (reusing the existing `CONFIG_DIR`
constant from `config.py`). Extended from the old single `toggle` message to
three: `start`, `stop`, `quit`.

`App` gets two new handlers alongside the existing `_on_toggle`/`_on_quit`,
both reusing `_on_toggle` rather than duplicating start/stop logic:

```python
def _on_hotkey_start(self) -> None:
    if self.controller.is_recording:
        GLib.idle_add(self.transcript_window.show_window)  # just raise it
    else:
        self._on_toggle()  # starts recording + shows window, same as today

def _on_hotkey_stop(self) -> None:
    if self.controller.is_recording:
        self._on_toggle()  # stops recording
```

`quit` reuses the existing `_on_quit` directly.

Also: `TranscriptWindow.show_window()` currently only calls `show_all()`,
which doesn't raise/focus a window that's open but buried behind others.
Add `self.present()` — benefits the existing tray-click path too, and is
required for "bring it to the front".

**Trigger side** — `dictation_ctl.py` (repo root, standalone, not imported by
the app), taking one argument: `start` / `stop` / `quit`. Connects to the
socket and sends the message. For `start`: if the connect fails (socket
missing → app not running), shells out to the existing `dictation start`
launcher (single source of truth for "how to launch the app" stays in that
script), polls briefly for the socket to appear, then sends `start`.
`stop`/`quit` are no-ops if the socket isn't there.

**GNOME binding** — three custom keyboard shortcuts, each pointed at
`.venv/bin/python /path/to/dictation_ctl.py <start|stop|quit>`, set up with
the correct relocatable-schema `:PATH` syntax. User runs these themselves
(desktop settings change) — documented in the README.

## Files touched

- `main.py` — re-add `ControlSocket`, wire `_on_hotkey_start`/`_on_hotkey_stop`,
  close the socket in `_on_quit`.
- `transcript_window.py` — `show_window()` calls `self.present()`.
- `dictation_ctl.py` — new file.
- `tests/step7_hotkey_control/` — socket dispatch tests + `dictation_ctl.py`
  behavior tests.
- `CLAUDE.md` project structure — add `dictation_ctl.py` entry.
- `README.md` — the `gsettings` recipe for binding the three shortcuts.

## Not touched

- `dictation` bash script — reused as-is.
- Tray click path — unaffected, still goes through `_on_toggle`.

## Verification

1. Test suite passes.
2. Manual: run `main.py`, then `dictation_ctl.py start/stop/quit` in another
   terminal, confirm each does the right thing including from-nothing start.
3. Manual (real desktop): bind the three GNOME shortcuts per the README
   recipe, verify each with `notify-send` first, then confirm real keypresses
   work end-to-end.
