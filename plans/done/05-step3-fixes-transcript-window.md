# Step 3 fixes — transcript window reliability

**Status: done**

Follow-up to [Step 3](04-step3-tray-app.md): the tray/popup flow is built, but manual testing surfaced a hang bug plus one missing UX behavior. This plan covers both, in order, before Step 3 is considered fully verified.

## 1. Fix the Stop-recording hang (bug)

**Files:** `output.py`

- `type_into()` calls `subprocess.run(["xdotool", "windowactivate", "--sync", ...])` and `subprocess.run(["xdotool", "type", ...])` with no timeout. When the captured `window_id` can't actually take focus (e.g. it's the tray/panel, not a real app window), `--sync` blocks forever.
- This hang happens inside `App._toggle_worker`'s `with self._toggle_lock:` block, so the lock is never released — the tray label never flips back to "Start recording", and the next click just queues up behind a dead lock forever (matches the reported "nothing is transcribed" symptom).
- **Fix:** add a `timeout=` to both `subprocess.run` calls in `output.py`, catch `subprocess.TimeoutExpired` alongside the existing `CalledProcessError`/`FileNotFoundError`, and fall back to clipboard on timeout same as today's fallback path.
- Out of scope for this pass: fixing *which* window gets captured (the tray/panel vs. the real target app) — that's a separate focus-timing issue, not required to stop the hang. Not touching it now.

**Verify:** trigger a stop with a window_id that can't be activated (or temporarily point `windowactivate` at a bogus id) and confirm `type_into` returns within the timeout instead of hanging, and the tray label still flips back.

## 2. Auto-scroll the transcript view (new behavior)

**Files:** `transcript_window.py`

- `set_partial()` / `append_final()` currently just call `self._buffer.set_text(...)` — the `Gtk.ScrolledWindow` doesn't follow new content down.
- **Fix:** after each buffer update, scroll the view to the end (e.g. `self._text_view.scroll_to_iter(self._buffer.get_end_iter(), ...)` or move the scrolled window's vertical adjustment to its upper bound).

**Verify:** speak a transcript long enough to overflow the popup's visible height, confirm the view stays pinned to the latest line instead of staying scrolled at the top.

## 3. Confirm existing behaviors survive the bug fix (no new code expected)

These are already implemented in `transcript_window.py` / `main.py` but were untestable while item 1 was hanging — confirm they work as designed, don't rewrite unless testing shows otherwise:

- **Append across Start/Stop cycles:** Stop, then Start again without closing the window → new segment appends below the old text (`begin_new_segment`, `transcript_window.py`).
- **Close (✕) resets state:** closing the popup clears all transcript content and, if a recording is in progress, stops it and flips the tray label back to "Start recording" (`_on_delete_event` + `App._on_window_closed`).
- **Start after close shows a blank window:** since content is cleared on close, reopening shows the same window instance but visually blank/fresh — confirmed acceptable as "new popup" per user, no new window object needed.

## 4. Fix Stop→Start label flicker (bug, found during manual testing of item 1)

**Files:** `tray.py`

- AppIndicator/dbusmenu is known to occasionally deliver the `activate` signal twice for a single click. Each `activate` spawns a new worker thread (`App._on_toggle`), so a double-fire meant: stop (label → "Start recording"), then immediately start again (label bounces back to "Stop recording") — the reported flicker.
- **Fix:** debounce in `TrayIcon._on_toggle_clicked` — a second activation within `TOGGLE_DEBOUNCE_SECONDS` (0.5s) is dropped before it reaches `on_toggle()`.
- **Verified:** `tests/step3_tray_app/test_tray_debounce.py` constructs a real `TrayIcon` (GTK/AppIndicator libs available in this environment) and directly fires `_on_toggle_clicked` twice back-to-back, confirming only one toggle fires; a second test confirms genuinely separate clicks each still toggle.
- **Correction:** the initial 0.5s debounce window was too wide — it could swallow a genuinely fast manual Stop click made shortly after Start. Narrowed to 0.15s (still well above a true duplicate `activate`, which fires within milliseconds).

## 5. Menu item rebuild on label change (defensive, not the root cause)

**Files:** `tray.py`

- Applied a workaround where `TrayIcon.set_recording()` rebuilds `toggle_item` from scratch instead of mutating its label in place, on the theory that GNOME's dbusmenu proxy wasn't re-rendering in-place label changes. Kept as a defensive measure (harmless, verified not to break anything), but live testing (item 6) showed this wasn't the actual cause of the reported delay.

## 6. Real root cause: label update was blocked behind the slow stop() pipeline

**Files:** `main.py`

- Diagnosed by driving the app directly over its exported dbusmenu D-Bus interface (`com.canonical.dbusmenu`, found via `org.kde.StatusNotifierWatcher`) — sending real `Event("clicked", ...)` calls and timing exactly when the exported menu layout's label actually changed, independent of any GNOME Shell rendering behavior. Confirmed the label *did* flip correctly, but only **~6 seconds** after the Stop click.
- Root cause: `App._toggle_worker`'s stop branch called `GLib.idle_add(self.tray.set_recording, False)` only *after* `self.controller.toggle()` returned — and that call runs the full stop pipeline synchronously: `recorder.stop()` → `provider.stop()` (blocking Groq HTTP transcription request) → `output.type_into()` (xdotool). The multi-second wait for that pipeline is what read as "doesn't switch."
- **Fix:** flip the tray label immediately when Stop is clicked (optimistic UI), then run the slow `controller.toggle()` work in the background:
  ```python
  else:
      GLib.idle_add(self.tray.set_recording, False)
      self.controller.toggle()
  ```
- **Verified live**, end-to-end, using a synthetic microphone: created a PulseAudio null-sink, set it as the default input source, played a `espeak-ng`-generated "This is a test" clip into it while the real app recorded via Groq. Confirmed:
  - Label flip now happens within ~0.3s of the Stop click (down from ~6s), checked via repeated dbusmenu `GetLayout` polls.
  - The full pipeline completed correctly in the background: clipboard held `"Is the test."` (Groq's read of the synthetic TTS audio — expected quality loss from a robotic voice, not an app bug), no errors in the app log.
  - Original mic restored as default input source and the null-sink module unloaded afterward.

## 7. Start-recording latency (same class of issue, opposite direction)

**Files:** `controller.py`, `main.py`

- Measured (not guessed) where Start's latency came from by timing each step of `controller.start()` directly: `config.load()` ~0ms, `config.get_key()` (keyring lookup) ~177ms, `capture_focused_window()` ~5ms, `provider.start()` ~697ms (Soniox's websocket handshake), `recorder.start()` ~18ms. ~900ms total, almost all of it the provider connect.
- Unlike Stop, flipping the label immediately here isn't safe on its own: `recorder.start()` ran *after* `provider.start()`, so the mic wasn't capturing yet during that ~700ms — flipping the label earlier (tried before, per the old code comment) meant losing the first bit of speech.
- **Fix:** added `_BufferedSink` in `controller.py` — the recorder now starts immediately, feeding into a small buffer; `provider.start()` runs in a background thread and connects the buffer to `provider.feed_audio` once ready, flushing whatever piled up in order. `stop()` joins that background thread before calling `provider.stop()`, so a fast Stop-after-Start can't race a not-yet-connected provider; any connect-time exception is captured and re-raised from `stop()`.
- `main.py`'s start-path comment updated — no logic change needed there, since `controller.toggle()` now returns as soon as the recorder is capturing, not after the provider connects.
- Considered and declined: a persistent/singleton provider kept muted between recordings instead of buffering. Rejected because it wouldn't remove the keyring-lookup or audio-init cost (the ~200ms floor that's left), and would keep an idle Soniox websocket connection open for no benefit.
- **Verified:** `tests/step3_tray_app/test_buffered_sink.py` covers `_BufferedSink` (buffer-then-flush ordering, direct feed once connected) and a controller-level test with a provider whose `start()` sleeps 0.2s, asserting `controller.start()` returns in well under that time and a chunk fed mid-connect still reaches the provider correctly on stop. Full suite (33 tests) passes.
- **Verified live** with the same synthetic-mic harness, against the real Soniox provider: label flip after a Start click landed in ~0.27s (down from ~0.9s), and the transcript ("Uh, this is the new test.") came through correctly with no errors in the app log — confirming no audio was lost despite the connect now happening in the background.

## 8. Second Start-after-Stop still slow (found by user after item 7)

**Files:** `controller.py`, `main.py`

- User reported the *second* Start click (right after a Stop) was noticeably slower than the very first one. Measured `controller.start()`/`stop()` directly for two back-to-back cycles — `start()` was actually equal-or-faster the second time (30ms vs 202ms), ruling out any provider/keyring "cold start" effect.
- Real cause: `main.py`'s `_toggle_worker` held `self._toggle_lock` for the *entire* `controller.toggle()` call on Stop — including its slow tail (Soniox's `_listener_thread.join(timeout=5)`, up to 5s, plus `output.type_into`'s xdotool calls). The label flip (item 6) made Stop *look* instant, but the lock was still held underneath. A Start click arriving during that window queued behind the same lock and had to wait out the rest of the previous session's teardown — the "cold start" the user saw.
- **Fix:** split `controller.stop()`'s shared setup into `_prepare_stop()`, which captures `provider`/`window_id`/`connect_error` as locals and flips `is_recording` to `False` — all fast (recorder stop + a thread join that's already finished). Added `stop_async()`, which does that fast part synchronously then finishes the slow part (`provider.stop()` + `output.type_into()`) in a background thread using the captured locals (not live `self.` attributes), so it's safe even if a new `start()` runs concurrently and reassigns `self._provider`/`self._recorder`/etc. for the next session. `main.py` now calls `stop_async()` instead of `toggle()` for the Stop branch, so `_toggle_worker` releases the lock almost immediately instead of holding it through the slow teardown. `stop()` (still synchronous, used by `record_once()`/CLI) and `toggle()` are unchanged.
- **Verified:** `tests/step3_tray_app/test_stop_async.py` — one test confirms `stop_async()` returns in well under the provider's simulated 0.3s `stop()` delay and flips `is_recording` immediately; a second test starts a session, calls `stop_async()`, immediately starts a *second* session while the first's background teardown is still running, and confirms session 1's `provider.stop()`/`output.type_into()` used session 1's own provider/window/text — not corrupted by session 2 already being live. Full suite (35 tests) passes.
- **Verified live** with the same synthetic-mic harness: Stop → (0.3s pause, well clear of the 150ms tray debounce) → Start again. The second Start registered within ~0.19s of being clicked (previously would've waited out Soniox's teardown, several seconds), and session 1's transcript ("This is a test.") still landed correctly in the clipboard afterward with no errors — confirming the concurrent-session handoff is race-safe in the real app, not just in the unit test.
- Note found along the way: sending two `Event("clicked", ...)` calls under ~150ms apart trips the tray's own debounce (added earlier for the double-`activate` dbusmenu quirk) — expected behavior for genuinely simultaneous events, but worth remembering that any future timing test needs a gap bigger than `TOGGLE_DEBOUNCE_SECONDS` to reflect a real click, not an artifact of the test.

## Manual verification (needs a real desktop session)

1. Start recording, speak, Stop — confirm tray label flips back to "Start recording" without hanging.
2. Click Start again without closing the popup — confirm the new transcript appends below the previous one.
3. Speak enough text to overflow the popup height — confirm it auto-scrolls to keep the latest line visible.
4. Close the popup (✕) while idle and while recording — confirm content clears and tray label reads "Start recording" in both cases.
5. Click Start again after closing — confirm a blank popup appears and recording works normally.

## Dependencies
None new — same `PyGObject`/`xdotool` stack as Step 3.
