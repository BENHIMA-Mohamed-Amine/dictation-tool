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

Copy `.env.example` to `.env` and fill in your API keys (`GROQ_API_KEY`, `SONIOX_API_KEY`).
