# Clipboard-first output (Wayland auto-type doesn't work)

**Status: done**

## Bug

User reported never seeing the dictated transcript auto-typed into their Claude session. Diagnosed live on their machine:

- Session is native Wayland (GNOME Shell 46, `loginctl` reports `Type=wayland`).
- `xdotool getactivewindow` fails outright — `_NET_ACTIVE_WINDOW` isn't exposed. The only windows visible via XWayland are internal compositor bits (GNOME Shell, ibus, mutter) — none of the user's real app windows (terminal, Claude Desktop, VS Code) show up at all.
- `xdotool` only speaks X11/XWayland. It cannot see or inject input into native Wayland windows — this is a Wayland security boundary, not a timing bug. Claude Desktop specifically runs with `--ozone-platform=wayland`, confirming it's a genuine Wayland-native client.

So the originally-suspected bug ("focus captured at the wrong moment, e.g. the tray menu instead of the target window") isn't the real issue — `capture_focused_window()` has essentially always returned `None`/an unusable id, and every session has already been silently falling back to clipboard via the existing fallback path in `output.py`. Fixing *when* the window is captured wouldn't change anything, since none of these windows are visible to xdotool regardless of timing.

## Decision

Discussed three options (ydotool kernel-level injection, wtype, clipboard-done-properly). Picked **clipboard-first, done properly**:
- No new system dependencies or sudo-gated setup (ydotool needs a daemon + udev rule for `/dev/uinput`; out of scope for this pass).
- wtype relies on the Wayland virtual-keyboard protocol, which GNOME/Mutter deliberately blocks for regular clients — would just fail the same way xdotool does on this compositor.
- The actual gap isn't that clipboard-fallback doesn't work (it does — verified in prior live testing, the clipboard reliably held the transcript every time) — it's that the fallback is **silent**. The user has no way to know dictation finished and text is sitting in their clipboard.

## Fix

**Files:** `output.py`

- Keep the existing xdotool attempt as-is (best-effort; harmless on this system since it now fails fast with the timeout from the earlier hang fix, and would still work correctly on a plain X11 session).
- When `type_into()` falls through to `_copy_to_clipboard()`, fire a desktop notification (`notify-send`) after a successful clipboard copy: `"Dictation finished" / "Transcript copied — press Ctrl+V to paste"`. Same defensive pattern as the rest of `output.py` — catch `FileNotFoundError`/`CalledProcessError` and no-op if `notify-send` isn't installed, don't fail the whole flow over a missing notifier.
- No change to `controller.py`/`main.py` — this is entirely `OutputTyper`'s concern.

## Tests

- `tests/step2_auto_type/test_output.py`: add a test asserting `_copy_to_clipboard` triggers a `notify-send` call with the expected summary/body once xclip succeeds, and a test confirming a missing `notify-send` binary doesn't raise or block the clipboard copy itself.

## Manual verification (needs a real desktop session)
1. Dictate a sentence with the app running as-is (Claude Desktop or terminal focused) — confirm a desktop notification appears once recording stops, and the transcript is in the clipboard (`Ctrl+V` pastes it).
