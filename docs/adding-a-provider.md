# Adding a new STT provider

Adding a provider touches **two files**: a new `providers/<name>.py`, and one
line in `providers/__init__.py`. Nothing else — not the tray, not the settings
window, not the controller. If you find yourself editing those, something is
wrong with the design and not with your provider.

## 1. Write `providers/<name>.py`

Subclass `Provider` from `providers/base.py` and implement four methods.

```python
from typing import Callable, List, Optional

from providers.base import ISO_639_1_LANGUAGES, Provider

DEFAULT_MODEL = "their-model-id"


class AcmeProvider(Provider):
    name = "acme"            # registry + config key, lowercase
    display_name = "ACME"    # how it's spelled in the UI
    streaming = True         # True if it returns partials while you speak
    MODEL_LABEL = DEFAULT_MODEL
    LANGUAGES = ISO_639_1_LANGUAGES

    def configure(self, api_key, model=None, language=None, keyterms=None) -> None:
        ...

    def start(self, on_partial=None, on_final=None) -> None:
        ...

    def feed_audio(self, chunk: bytes) -> None:
        ...

    def stop(self) -> str:
        ...
```

### The class attributes

| Attribute | What it drives |
|---|---|
| `name` | Key in `PROVIDERS`, in `config.json`, and in the keyring. Lowercase. |
| `display_name` | Tray submenu entry and settings tab label. `"NVIDIA"`, not `"Nvidia"`. |
| `streaming` | Whether the provider emits partials. Informational — the controller drives both kinds the same way. |
| `MODEL_LABEL` | Shown read-only in the settings tab. One string: every provider so far has exactly one model worth using, so there's no dropdown. |
| `LANGUAGES` | `(label, code)` pairs for the language dropdown. `code=None` means auto-detect, i.e. *send no language hint*. Reuse `ISO_639_1_LANGUAGES` if the API takes plain `en`/`fr` codes; write your own list if it wants `en-US` style codes. **If the API requires a language, just omit the `None` entry** — the dropdown is built per provider, so it'll have no Auto option and nothing else needs to know. |

### The methods

**`configure(api_key, model, language, keyterms)`** — store settings, connect
nothing. `model` and `language` arrive as `None` when the user hasn't chosen
one; fall back to your own `DEFAULT_MODEL` (`self.model = model or DEFAULT_MODEL`).
`keyterms` is the global vocabulary-boost list — map it onto whatever the API
calls it (Groq stuffs it into `prompt`, Soniox has a real keyterms field).

**`start(on_partial, on_final)`** — open the connection. Called on a background
thread, so blocking here is fine and expected. Both callbacks are optional.

- `on_partial(text)` — the current in-flight guess. The transcript window
  **replaces** the live tail with it, so send the whole partial, not a delta.
- `on_final(text)` — settled text. **Appended**, so send only the new segment.

Batch providers (Groq) can ignore both and just reset their buffer.

**`feed_audio(chunk)`** — raw PCM from the mic: 16 kHz, mono, int16, little
endian (see `audio.py`). Called continuously from the recorder thread.

**`stop() -> str`** — close the connection and return the full transcript for
the session. Called on a background thread too. For batch providers this is
where the actual HTTP request happens.

### Threading

`start()`, `feed_audio()` and `stop()` all run off the GTK main loop, and
`on_partial`/`on_final` fire from whatever thread your SDK uses. Do **not**
touch GTK from any of them — the window marshals callbacks with
`GLib.idle_add` itself. Just call the callbacks.

## 2. Register it

```python
# providers/__init__.py
from providers.acme import AcmeProvider

PROVIDERS = {
    ...,
    "acme": AcmeProvider,
}
```

That's the whole wiring. The tray submenu, the settings tab, and
`--provider acme` on the CLI all come from iterating this dict.

## 3. The API key

Nothing to write. `ConfigStore.get_key("acme")` checks the OS keyring first,
then falls back to `ACME_API_KEY` in the environment — the env var name is
derived from `name`, not listed anywhere. Users set the key via
Settings → the provider's tab → Change.

Add the variable to `.env.example` so the fallback is discoverable.

## 4. Dependencies

```bash
uv add their-sdk
```

Never hand-edit `pyproject.toml`.

## 5. Test it

Add `tests/<step>/test_acme.py` with a fake transport — no real mic, no real
network. `tests/step1_cli_core/` has examples of driving a provider with
canned audio chunks. Then the real check:

```bash
uv run python main.py
```

Pick the provider in the tray, record, confirm text appears.

## Checklist

- [ ] `providers/acme.py` with all four methods and the five class attributes
- [ ] One line in `PROVIDERS`
- [ ] `ACME_API_KEY` added to `.env.example`
- [ ] `uv add` for any new SDK
- [ ] A test that doesn't need hardware
- [ ] Entry in the project-structure tree in `CLAUDE.md`
