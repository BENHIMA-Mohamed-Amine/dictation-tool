# General plan — Ubuntu tray dictation tool

## Context
Claude's built-in voice transcription misses domain-specific keywords and can't be used mid-conversation without switching modes. This tool is a standalone Ubuntu tray app: click a mic icon, pick a provider, speak, see the transcript live, and copy it out via the popup's Copy button (a global hotkey and auto-typing were both tried and later removed — see the Recording flow and Global hotkey sections below). Providers must be pluggable — adding a new one later shouldn't require touching the tray/audio/output code.

First three providers: **Soniox**, **NVIDIA (Nemotron ASR streaming)**, **Groq (Whisper)**.

## Provider research (confirmed via docs)
- **Soniox**: WebSocket streaming (`wss://stt-rt.soniox.com/transcribe-websocket`). Use the official Soniox Python SDK (handles handshake/config/reconnect) rather than raw websockets. Supports "context"/keyterms for vocabulary boosting — directly fixes the missed-keyword problem. True real-time partial + final tokens.
- **NVIDIA Nemotron ASR streaming**: hosted via `build.nvidia.com` NIM, gRPC streaming. Use the official `nvidia-riva-client` SDK rather than hand-writing gRPC stubs from `.proto` files. Free API key from build.nvidia.com. Supports word/boost list. Requires 16-bit mono audio.
- **Groq**: REST only (`POST https://api.groq.com/openai/v1/audio/transcriptions`), batch, `whisper-large-v3` / `whisper-large-v3-turbo`, supports a `prompt` field for vocabulary hints, 25MB file limit. Use raw `requests` — one stateless multipart POST, not enough surface to justify their SDK. Fast enough to fake "live" by transcribing short rolling buffers (e.g. every 3-5s).

Each provider declares `streaming: bool` so the UI knows whether to show incremental partials or periodic batch updates.

## Recording flow
1. Click tray mic → start recording. (A global hotkey was tried as a second trigger — see below.)
2. Live partials shown in a small transcript popup as they stream in (Soniox/NVIDIA); Groq updates the popup every ~4s from rolling batch calls.
3. Click again → stop recording, get final transcript text, appended into the popup.
4. Transcript popup's Copy button is the only output mechanism — auto-type via `xdotool` and clipboard-on-stop were both tried and removed (see `plans/done/08-remove-auto-output.md`): `xdotool` can't act on native Wayland windows, and the clipboard-with-notification fallback still had a confusing multi-second lag before it was actually ready.

## Global hotkey (Wayland-safe) — tried and removed
Ubuntu defaults to Wayland, which blocks apps from registering global key listeners directly. So the plan was:
- App listens on a Unix socket (`~/.config/dictation-tool/ctl.sock`) for a `toggle` message.
- A tiny `hotkey_daemon.py` script just writes `toggle` to that socket.
- User binds `python3 hotkey_daemon.py` to a key combo via **GNOME Settings → Keyboard → Custom Shortcuts** (native OS feature) — can't be set programmatically, one-time manual step after the app works.

This was built and the socket mechanism itself worked (verified directly), but the GNOME keybinding never actually fired the command when pressed — a GNOME/environment integration issue, not worth continuing to debug for a second trigger on a feature that already works from the tray. Removed — see `plans/done/09-step4-global-hotkey.md` and `plans/done/10-remove-global-hotkey.md`. Tray click is the only trigger.

## Folder structure
```
~/projects/dictation-tool/
├── main.py
├── tray.py
├── controller.py
├── settings_window.py
├── transcript_window.py
├── hotkey_daemon.py
├── audio.py
├── config.py
├── providers/
│   ├── __init__.py
│   ├── base.py
│   ├── soniox.py
│   ├── nvidia.py
│   └── groq.py
├── pyproject.toml
├── README.md
├── design/                    # UI mockups
├── plans/                     # tracked plan files for big features (status: proposed/approved/done/deferred)
│   └── done/
└── docs/
    └── general-context/       # this file + features/design/class-design — background reference, not tracked plan files
        ├── 00-general-plan.md
        ├── 01-features.md
        ├── 02-design.md
        └── 03-class-design.md
```

## Dependencies (managed via `uv`/`pyproject.toml`)
`PyGObject` (AppIndicator3/GTK — needs `sudo apt install gir1.2-ayatanaappindicator3-0.1 python3-gi` at the OS level, noted in README), `sounddevice`, `keyring`, `soniox` (official SDK), `nvidia-riva-client`, `requests` (Groq). Not dockerized — this app is tied to the host desktop session (D-Bus tray, mic device, GNOME Keyring), so containerizing it would mean mounting nearly the whole host session in anyway.

## Build order
1. `config.py` + `providers/base.py` + `providers/__init__.py` registry (skeleton, no real providers yet).
2. `audio.py` mic capture, verified by recording to a WAV and playing it back.
3. `providers/groq.py` first (simplest, REST/batch) + `controller.py` — get one full CLI-only path working: record → transcribe → print text to terminal. No tray yet.
4. `tray.py` + `transcript_window.py` wired to the controller from step 3. Copy button is the output mechanism (an `output.py`/`OutputTyper` auto-type step was tried after this and later removed — see `plans/done/08-remove-auto-output.md`).
5. `hotkey_daemon.py` + `ControlSocket` in `main.py`, wired to `controller.toggle()`.
6. `providers/soniox.py` (WebSocket streaming via SDK), then `providers/nvidia.py` (gRPC streaming via SDK) — same `Provider` interface, so nothing outside `providers/` changes.
7. `settings_window.py` (global keyterms + per-provider tabs), wired to `ConfigStore` + `keyring`.

## Verification
- After step 4: run `main.py`, click tray icon, speak a sentence containing a jargon word, stop, confirm transcript popup shows the text and the Copy button copies it correctly.
- After step 6: repeat with Soniox and NVIDIA selected, confirm partial results appear while speaking (not just at the end).
- After step 7: add a keyterm in Settings, confirm the same jargon word transcribes correctly where it previously didn't.
- `python main.py &` then `python hotkey_daemon.py` from another terminal to confirm the socket toggle works before wiring it to an actual GNOME keybinding.
