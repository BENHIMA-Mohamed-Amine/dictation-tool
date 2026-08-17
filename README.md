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

For bash tab-completion of `start`/`stop`/`status`, add to `~/.bashrc`:

```
complete -W "start stop status" dictation
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

### Keyboard shortcuts (optional)

Wayland (GNOME's compositor here) doesn't let ordinary apps register their
own global hotkeys, so the trigger has to be a GNOME custom keyboard
shortcut that runs a command. The running app listens on a control socket
(`~/.config/dictation-tool/ctl.sock`) for `start`/`stop`/`quit`;
`dictation_ctl.py` sends those, launching the app first via `dictation start`
if it isn't running yet.

- **start** — launches the app if it's not running and starts recording; if
  it's already running, brings the transcript window to the front (and
  starts recording if it wasn't already).
- **stop** — stops recording, app keeps running.
- **quit** — stops the app completely.

Bind three shortcuts with `gsettings`. **The custom-keybinding schema is
relocatable** — every `set` below must include the `:/org/...` path suffix,
or GNOME accepts the write silently but the shortcut never fires (this was
tried once before without the suffix and quietly did nothing).

Bindings used below — `Super+D` alone is already GNOME's own "Show Desktop"
shortcut (as is `Ctrl+Super+D`), so plain `Super+<letter>` combos are mostly
taken. `Super+Shift+<letter>` is free across every GNOME keybinding schema
on a stock install, and only needs two modifiers held down:

```bash
BASE=org.gnome.settings-daemon.plugins.media-keys
REPO=/home/benhima/projects/dictation-tool
PY="$REPO/.venv/bin/python"

gsettings set $BASE custom-keybindings "['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/', '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/', '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/']"

gsettings set $BASE.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ name 'Dictation: start'
gsettings set $BASE.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ command "$PY $REPO/dictation_ctl.py start"
gsettings set $BASE.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ binding '<Super><Shift>d'

gsettings set $BASE.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/ name 'Dictation: stop'
gsettings set $BASE.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/ command "$PY $REPO/dictation_ctl.py stop"
gsettings set $BASE.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/ binding '<Super><Shift>s'

gsettings set $BASE.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ name 'Dictation: quit'
gsettings set $BASE.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ command "$PY $REPO/dictation_ctl.py quit"
gsettings set $BASE.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ binding '<Super><Shift>q'
```

If any of `Super+Shift+D/S/Q` turn out to be taken by something on your
system (extensions can add their own), check **Settings → Keyboard → View
and Customize Shortcuts** and swap the `binding` value for that slot.

**Verify each binding fires before trusting it.** Temporarily set a
`command` to `notify-send test` and press the key — no notification means
the *binding* itself isn't registered (bad combo, conflict, or a typo in the
`:/org/...` path suffix), independent of anything in this app. Only once
that works, switch the command back to the real `dictation_ctl.py` line.

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
