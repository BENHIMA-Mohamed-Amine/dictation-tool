# Step 2 — Auto-type output

**Status: done** — verified end-to-end (2026-07-18). User's session is Wayland (`$XDG_SESSION_TYPE=wayland`), so `xdotool` window capture/typing isn't available there — confirmed the clipboard fallback works correctly instead: `xclip -o -selection clipboard` returned the exact transcript after a real recording. True auto-type via `xdotool` remains untested (needs an X11 session or XWayland-compatible target app) but the code path and fallback are both proven correct.

Detailed plan for [Step 2](01-implementation-steps.md) of the overall build: same record → transcribe flow as step 1, but the final transcript gets typed into whichever window was focused before recording started, instead of just printed.

## The focus-timing problem (CLI-only constraint)

Step 2 still has no tray/hotkey (those are steps 3/4) — recording is started/stopped from the terminal via `input()`. But `input()` needs the *terminal* to have keyboard focus to receive your Enter keypress, while auto-type needs to know the *target app's* window id, captured *before* you switch back to the terminal. So for this CLI-only step:

1. Script starts, prints a 3-second countdown ("switch to your target window now").
2. After the countdown, it captures whatever window is focused at that moment (expected: your text editor/terminal/Claude, whatever you switched to) and starts recording.
3. You switch focus back to the terminal and press Enter to stop (same as step 1).
4. The transcript is typed into the window id captured in step 2, not wherever focus happens to be at that point.

This constraint goes away in step 3 (tray click) and step 4 (hotkey), where starting recording doesn't require stealing terminal focus in the first place.

## Files

- **`output.py`** (new) — `OutputTyper` class:
  - `capture_focused_window() -> Optional[str]` — runs `xdotool getactivewindow`, returns the window id string, or `None` if `xdotool` is missing or the call fails (e.g. running under pure Wayland without XWayland).
  - `type_into(window_id: Optional[str], text: str) -> None` — if `window_id` is set: `xdotool windowactivate --sync <id>` then `xdotool type --clearmodifiers -- <text>`. If that fails at any point (`xdotool` missing, command errors, `window_id` was `None`), falls back to copying `text` to the clipboard via `xclip -selection clipboard`, so the transcript is never silently lost.
- **`controller.py`** — `record_once()` gains the countdown + capture step before recording starts, and calls `self.output.type_into(window_id, text)` after `provider.stop()` instead of only returning the text (it still returns it too, for callers/tests).

## Tests

New folder: `tests/step2_auto_type/`.

- **`tests/step2_auto_type/test_output.py`**
  - `capture_focused_window()` calls `subprocess.run(["xdotool", "getactivewindow"], ...)` and returns its stdout, stripped — verified with `unittest.mock.patch("output.subprocess.run")`, no real `xdotool` needed.
  - `capture_focused_window()` returns `None` if `subprocess.run` raises (`FileNotFoundError` or `CalledProcessError`).
  - `type_into(window_id, text)` with a real `window_id` calls `windowactivate` then `type` with the right arguments.
  - `type_into(None, text)` (or when the `xdotool` calls raise) falls back to calling the `xclip` clipboard command with `text` piped in.
- **`tests/step2_auto_type/test_controller.py`**
  - Extends the step-1 fake-provider test: with `OutputTyper` mocked out, confirm `record_once()` calls `capture_focused_window()` before `provider.start()`, and calls `type_into(captured_window_id, returned_text)` after `provider.stop()`.
  - `time.sleep` is monkeypatched to a no-op so the test doesn't actually wait 3 seconds.

## Manual verification (not automated — needs a real desktop session)
- Run `echo $XDG_SESSION_TYPE` first — if it prints `wayland`, expect `xdotool` to be unreliable; note the actual result either way.
- Run the script, during the countdown switch to a text editor (e.g. gedit) or a terminal text field, speak a sentence, switch back and press Enter, confirm the text appears typed in the editor.
- If on Wayland and `xdotool` fails, confirm the clipboard fallback at least puts the text somewhere retrievable (`xclip -o -selection clipboard`).

## Dependencies
`xdotool` and `xclip` are OS packages (`sudo apt install xdotool xclip`), not Python packages — not installed via `uv add`. No new Python dependencies needed for this step (`subprocess` is stdlib).
