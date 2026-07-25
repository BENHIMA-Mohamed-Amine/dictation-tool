# dictation-tool

Ubuntu tray dictation tool with pluggable STT providers (Soniox, NVIDIA, Groq).

## Setup

Python dependencies are managed with `uv` (`uv sync`).

OS packages required (not installed via `uv`):

```
sudo apt install libgirepository-2.0-dev libcairo2-dev gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 python3-dev
```

- `libgirepository-2.0-dev`, `libcairo2-dev`, `python3-dev` — build headers needed to install the `pygobject` Python package (`uv add pygobject` will fail without these).
- `gir1.2-gtk-3.0`, `gir1.2-ayatanaappindicator3-0.1` — the actual GTK3/tray-indicator bindings used at runtime. Note: on current Ubuntu the GObject-introspection namespace is `AyatanaAppIndicator3`, not `AppIndicator3` — that's what the code imports.

Then set an API key (below) and you're ready to run.

## Running

Put the launcher on your PATH once:

```
ln -s "$PWD/dictation" ~/.local/bin/dictation
```

Then, from anywhere:

```
dictation start     # launches the tray app in the background
dictation stop
dictation status
```

Output goes to `$XDG_RUNTIME_DIR/dictation-tool.log` (usually
`/run/user/1000/dictation-tool.log`) — check it there if `start` seems to do
nothing.

To run it in the foreground instead, e.g. while debugging:

```
uv run python main.py
```

### Using it

The tray icon and the transcript window both have a Start/Stop control; the
window's button is the everyday one, because a tray menu closes on every click.
Text lands in the transcript window, which is editable — fix a word mid-sentence
and the correction survives as you keep speaking. **Copy** is the only way to get
the text out; there is deliberately no auto-type or clipboard-on-stop (it was
tried twice and removed — see `plans/done/08-remove-auto-output.md`).

To start it automatically at login, drop a desktop entry in
`~/.config/autostart/` whose `Exec=` is the absolute path to `dictation start`.

## API keys

Preferred: tray → **Settings** → provider tab → **Change**. Keys entered there go
straight into the OS keyring (GNOME Keyring), never into `config.json`, and are
never displayed back.

Alternative: copy `.env.example` to `.env` and fill in `GROQ_API_KEY`,
`SONIOX_API_KEY`, `NVIDIA_API_KEY`. `.env` is only a fallback — the keyring wins
if both are set.

## Settings

Tray → **Settings**:

- **Keyterms** — one global vocabulary-boost list, applied to whichever provider
  is active. Type a term, press Enter; click × to remove.
- **Per provider** — the model in use (read-only: one model per provider), API
  key, and language. Language defaults to Auto-detect for Groq and Soniox;
  NVIDIA requires an explicit language. Saved keys show as
  `gsk_••••••••3f2a` — first and last four characters only.

Settings live in `~/.config/dictation-tool/config.json`.

## Adding a provider

See [docs/adding-a-provider.md](docs/adding-a-provider.md) — a new backend is a
new file in `providers/` plus one line in `providers/__init__.py`.

## Docs

- [docs/adding-a-provider.md](docs/adding-a-provider.md) — the `Provider`
  contract, step by step.
- [docs/general-context/](docs/general-context/) — background: the
  [plan](docs/general-context/00-general-plan.md),
  [features](docs/general-context/01-features.md),
  [UI design](docs/general-context/02-design.md),
  [class design](docs/general-context/03-class-design.md).
- [plans/](plans/) — one file per big feature, with its status. Finished ones
  move to [plans/done/](plans/done/) and are the best record of *why* something
  works the way it does (including what was tried and removed).
- [CLAUDE.md](CLAUDE.md) — working guidelines, plus a map of every file in the
  project.

Tests live in `tests/`, one folder per build step, and need no mic or network:

```
uv run pytest
```

### Provider APIs

- [Groq speech-to-text](https://console.groq.com/docs/speech-to-text) — batch REST, `whisper-large-v3-turbo`.
- [Soniox real-time STT](https://soniox.com/docs/stt/rt/real-time-transcription) — websocket streaming, `stt-rt-v5`.
- [NVIDIA Riva ASR](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/asr/asr-overview.html) — gRPC streaming against the hosted `nemotron-asr-streaming` NVCF function.
