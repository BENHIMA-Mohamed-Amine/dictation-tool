# Step 3 — Tray app

**Status: done** — see also [05-step3-fixes-transcript-window.md](done/05-step3-fixes-transcript-window.md) for the reliability/latency fixes found during manual verification.

Detailed plan for [Step 3](01-implementation-steps.md) of the overall build: replace the manual CLI script with the real UI — click the tray mic menu item to start/stop, see the transcript live in a popup, provider switchable from a submenu. Same record → transcribe → auto-type pipeline underneath (steps 1-2), just triggered by clicks instead of terminal `input()`.

## Why `controller.py` needs to change shape

Steps 1-2's `record_once()` is a single blocking call: it waits on `input()` in the terminal to know when to stop. A tray app can't work that way — "start" and "stop" are two separate click events with the recording happening in between while the rest of the UI stays responsive. So `DictationController` needs non-blocking `start()` / `stop()`, with a `toggle()` on top (per the class design in `docs/general-context/03-class-design.md`, which specified this from the start).

This is a refactor, not a rewrite: `start()`/`stop()` become the real implementation, and `record_once()` (kept for the CLI / for steps 1-2's tests, which stay green) becomes a thin wrapper: `start()` → `input()` → `stop()`. Single source of truth, no duplicated recording logic between CLI and tray paths.

## Files

- **`controller.py`** (refactor)
  - `start(provider_name=None, on_partial=None, on_final=None)` — everything `record_once()` used to do up through `recorder.start()`: build/configure the provider, capture focused window, start the recorder. Non-blocking, returns immediately (recording continues via the provider's own audio callback thread).
  - `stop() -> str` — stops the recorder, calls `provider.stop()`, calls `self.output.type_into(...)`, returns the text.
  - `toggle(provider_name=None, on_partial=None, on_final=None) -> Optional[str]` — internal `self._recording` flag; if not recording, calls `start()` and returns `None`; if recording, calls `stop()` and returns the transcript.
  - `record_once(provider_name=None) -> str` — now implemented as `start(...)`, `input(...)`, `stop()`. Behavior unchanged, existing step-1/2 tests keep passing untouched.
- **`transcript_window.py`** (new) — `TranscriptWindow` class, a small `Gtk.Window` with a read-only `Gtk.TextView` and a Copy button (`Gtk.Clipboard`).
  - `show()` / `hide()`.
  - `set_partial(text)` — replaces the "in progress" line.
  - `append_final(text)` — commits finalized text to the window's permanent content.
  - **Threading note**: provider callbacks (especially Soniox's listener thread) fire from a background thread, but GTK widgets can only be touched from the main GTK loop. Every call into `TranscriptWindow` from a provider callback must be wrapped in `GLib.idle_add(...)`, not called directly.
- **`tray.py`** (new) — `TrayIcon` class using `AppIndicator3`:
  - Menu: a top item showing a mic icon, labeled "Start recording" / "Stop recording" depending on state — clicking it calls `controller.toggle(...)`.
  - A "Provider" submenu built from `PROVIDERS.keys()`, radio-style, checked item reflects `ConfigStore.load()["selected_provider"]`; clicking an entry saves the new selection via `ConfigStore.save(...)`.
  - "Quit" — stops the app.
  - No "Settings" item yet — that's step 6; adding a menu item that does nothing yet would be dead UI.
- **`main.py`** (replaces the placeholder) — the `App` orchestrator:
  - Builds `ConfigStore`, `TranscriptWindow`, `OutputTyper`, `DictationController`, `TrayIcon`.
  - Wires `on_partial`/`on_final` callbacks to `GLib.idle_add(transcript_window.set_partial, ...)` / `GLib.idle_add(transcript_window.append_final, ...)`.
  - Runs `start()`/`stop()` on a background thread (not the GTK main thread) so opening a provider's connection (e.g. Soniox's up-to-10s connect timeout) never freezes the tray/menu.
  - Runs `Gtk.main()`.

## Tests

New folder: `tests/step3_tray_app/`.

- **`tests/step3_tray_app/test_controller_toggle.py`**
  - `toggle()` called once with a fake provider starts recording (provider `configure`/`start` called, recorder `start` called) and returns `None`.
  - `toggle()` called a second time stops it (recorder `stop`, provider `stop`, `output.type_into` called) and returns the transcript.
  - `record_once()` still behaves exactly as in step 1/2's tests (regression check — those existing test files are not touched).

`tray.py` and `transcript_window.py` are not automatically tested: both require a real GTK/AppIndicator display session to construct, which isn't available in a headless test run. They're covered by manual verification only, same as the audio/mic reliance in earlier steps.

## Manual verification (needs a real desktop session)
- Run `main.py`. Confirm the mic icon appears in the top bar (per the design in `design/tray_menu.svg`).
- Click the icon, click "Start recording", speak a sentence, confirm the transcript popup updates live.
- Click the icon again, click "Stop recording" (label should have changed), confirm the popup shows the final text and — per step 2's already-verified behavior on this machine — the clipboard gets the text (Wayland fallback).
- Open the Provider submenu, switch from Soniox to Groq, repeat a recording, confirm it still works end-to-end with the new provider.
- Click Quit, confirm the tray icon disappears and the process exits.

## Dependencies
`PyGObject` (`AppIndicator3`/`GLib`/`Gtk` bindings) via `uv add pygobject`. Also needs the system package `gir1.2-ayatanaappindicator3-0.1` (`sudo apt install gir1.2-ayatanaappindicator3-0.1 gir1.2-gtk-3.0`) — add to README alongside `xdotool`/`xclip`.
