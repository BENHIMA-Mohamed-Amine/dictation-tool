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
