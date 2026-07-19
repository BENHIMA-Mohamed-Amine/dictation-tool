# Class design

- **`Provider` (ABC, `providers/base.py`)** — `name`, `streaming: bool`, `configure(api_key, model, language, keyterms)`, `start(on_partial, on_final)`, `feed_audio(chunk)`, `stop() -> str`.
- **`SonioxProvider` / `NvidiaProvider` / `GroqProvider`** — one implementation per backend. `PROVIDERS = {"soniox": SonioxProvider, ...}` registry dict in `providers/__init__.py` — the extension point; adding a provider later is a new file + one dict entry, nothing else changes.
- **`ConfigStore` (`config.py`)** — reads/writes `~/.config/dictation-tool/config.json` (selected provider, global keyterms, per-provider model/language); wraps `keyring` for `get_key(provider)` / `set_key(provider, value)`.
- **`AudioRecorder` (`audio.py`)** — wraps `sounddevice`; `start(on_chunk)` / `stop()`.
- **`DictationController` (`controller.py`)** — the single source of truth for a recording session. Owns `AudioRecorder` and the active `Provider`. Exposes `start()`/`stop()`/`stop_async()`/`toggle()`. Both `TrayIcon` (mic click) and the hotkey socket call the same methods — no duplicated start/stop logic. No output/window-typing responsibility — callers get the transcript from `stop()`'s return value or, for the tray app, from the popup.
- **`TrayIcon` (`tray.py`)** — `AppIndicator3` icon + menu (mic toggle → `controller.toggle()`, provider submenu writing to `ConfigStore`, Settings, Quit).
- **`SettingsWindow` (`settings_window.py`)** — the tabbed GTK window (global keyterms + per-provider tabs); reads/writes through `ConfigStore`.
- **`TranscriptWindow` (`transcript_window.py`)** — live/partial + final transcript popup with a Copy button. That button is the only way to get the transcript out — auto-type/clipboard-on-stop (`OutputTyper`/`output.py`) was tried and removed: `xdotool` can't see or activate native Wayland windows, and the clipboard-with-notification fallback still had a confusing multi-second lag before it was ready. The Copy button reads the buffer directly at click time, so there's no lag to get confused by.
- **`ControlSocket` (`main.py`)** — Unix socket server for the hotkey `toggle` message, calls `controller.toggle()`.
- **`App` (`main.py`)** — orchestrator: builds `ConfigStore`, `DictationController`, `TrayIcon`, `ControlSocket`, runs the GTK main loop.
