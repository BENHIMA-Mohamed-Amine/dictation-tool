# Remove auto-output entirely (xdotool type, clipboard, notification)

**Status: done**

## Why

Auto-type (`xdotool`) never worked on this user's Wayland session (confirmed: `xdotool` can't see or activate native Wayland windows — a platform limitation, not a bug). The clipboard-copy-with-notification fallback added afterward ([done/06](done/06-clipboard-first-output.md)) and the cross-session accumulation fix ([done/07](done/07-clipboard-matches-popup-transcript.md)) both work correctly when checked at the right moment — verified live, repeatedly — but the background teardown (Soniox's session drain) takes a few seconds, and the user keeps checking before that finishes, seeing stale clipboard content and reading it as still broken. The `notify-send` signal meant to mark "now it's ready" isn't visibly showing up for the user either.

Rather than keep patching a background-timing problem the user can't reliably observe, remove the automatic output path entirely. The transcript popup already has a manual "Copy" button (`transcript_window.py`) that reads the currently-displayed `Gtk.TextBuffer` directly at the moment of the click — no background thread, no timing window, synced by construction. That becomes the only way to get the text out.

## Scope: everything

- `output.py` — deleted. `OutputTyper` (`capture_focused_window`, `type_into`, `_copy_to_clipboard`, `_notify_clipboard_fallback`) is gone.
- `controller.py`:
  - Remove the `output` constructor parameter and `self.output`.
  - Remove `self._window_id` and the `capture_focused_window()` call in `start()`.
  - `stop()` / `_prepare_stop()` / `stop_async()` no longer call `type_into()` or take a `build_output_text` parameter — they just stop the recorder/provider and return the session's transcript (for `stop()`/CLI) or nothing (for `stop_async()`, tray path).
- `main.py`:
  - Remove the `OutputTyper` import/instance and no longer pass `output=` to `DictationController`.
  - Remove `_TranscriptLog` entirely — it only existed to reconstruct the accumulated text for the clipboard write, which no longer happens. The popup's own buffer is the only accumulated-text store now.
  - `stop_async()` call in `_toggle_worker` drops the `build_output_text=` argument.
- Tests:
  - Delete `tests/step2_auto_type/` (both files exist only to test `OutputTyper`/the window-capture-and-type behavior).
  - Update `tests/step3_tray_app/test_controller_toggle.py`, `test_stop_async.py`, `test_buffered_sink.py` to drop the `output=`/`fake_output` wiring and any assertions on `type_into`/`capture_focused_window`.
  - Delete `tests/step3_tray_app/test_transcript_log.py` (tests the now-deleted `_TranscriptLog`).
- Docs:
  - `README.md` — drop the `xdotool`/`xclip` system package line and their bullet descriptions.
  - `CLAUDE.md` project structure — remove the `output.py` entry, update `controller.py`'s one-line description (no longer mentions auto-type).
  - `.env.example` unaffected (API keys only, unrelated to output).

## Not touched
- `transcript_window.py`'s Copy button — already the correct mechanism, no changes needed.
- CLI (`record_once()` / `controller.py`'s `__main__` block) — already prints the transcript to stdout regardless of auto-type/clipboard, so this removal doesn't reduce CLI usefulness.

## Verification
- Full test suite green after the removal (no leftover references to `output`, `OutputTyper`, `_TranscriptLog`, `build_output_text`).
- Manual: run the app, dictate across two Start/Stop cycles without closing the popup, click the popup's Copy button, confirm `Ctrl+V` matches exactly what's displayed — no background wait involved.
