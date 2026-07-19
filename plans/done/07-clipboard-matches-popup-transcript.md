# Clipboard should match the full popup transcript, not just the latest session

**Status: done**

## Bug

Confirmed with the user: the popup accumulates text across every Start/Stop cycle done without closing the window (each new segment appends below the last, via `begin_new_segment`/`append_final`). But the clipboard only ever gets the transcript from the single most-recent Stop click — `controller.stop()`/`stop_async()` calls `output.type_into(window_id, text)` with just `provider.stop()`'s return value for that one session.

So after two or three Start/Stop cycles without closing the popup, the popup shows everything so far, but `Ctrl+V` only pastes the last segment — not synced.

## Fix

**Files:** `controller.py`, `main.py`

- `DictationController.stop_async()` gets an optional `build_output_text: Callable[[str], str]` parameter — a hook that transforms the just-finished session's raw text into whatever should actually be sent to `output.type_into()`. Defaults to identity (no behavior change for existing callers/tests). `stop()` (synchronous, CLI path) and `toggle()` are untouched — the CLI's `record_once()` has no concept of "popup accumulation," so its per-session output stays as-is.
- `main.py`'s `App` gets a small thread-safe transcript accumulator (a plain string behind a `threading.Lock`, *not* reading `TranscriptWindow`'s GTK state from a background thread — `stop_async()`'s slow part runs off the GTK main thread, and touching a GTK widget's internals from there would be its own bug). Built from each session's own `provider.stop()` return value, not from the `on_final` callback stream — this works uniformly for both streaming providers (Soniox, which also fires `on_final` progressively) and batch providers (Groq, which never fires `on_final` at all and only has a text at the very end). Using the callback stream instead would leave Groq's clipboard permanently empty.
- On Stop, `main.py` calls `self.controller.stop_async(build_output_text=self._append_to_transcript_log)`, where that method appends the session's text (with the same blank-line segment separator the popup uses) and returns the *full* accumulated log — that's what actually gets typed/copied.
- Closing the popup (✕) resets this accumulator too, alongside the existing `TranscriptWindow.reset()`, so a fresh popup starts a fresh clipboard log.
- Known accepted limitation, not fixed here (edge case, not the reported bug): if a user starts a *second* recording while the *first* one's background teardown (e.g. Soniox's multi-second drain) is still running, and the second one finishes first, the accumulator would append out of chronological order. Not fixing now — normal usage waits for one cycle to finish before starting the next; ordering-safe queuing would be speculative complexity for a scenario nobody has hit yet.

## Tests

- `tests/step3_tray_app/`: a controller-level test confirming `stop_async(build_output_text=...)` calls `output.type_into` with the transformed text, not the raw session text (default behavior unchanged when the parameter is omitted).
- A `main.py`-level (or extracted helper) test confirming the accumulator concatenates two sessions' text with a separating newline, and resets to empty after a simulated window-close.

## Manual verification (needs a real desktop session)
1. Start, speak, Stop. Start again (without closing popup), speak something else, Stop. Confirm `Ctrl+V` now pastes *both* segments, matching the popup exactly.
2. Close the popup, Start, speak, Stop. Confirm the clipboard only has this new segment, not anything from before the close.
