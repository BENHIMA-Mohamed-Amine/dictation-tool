# Step 6 — Settings window

**Status: approved** — implemented; awaiting the manual end-to-end test before moving to `plans/done/`.

Implements the last step of `plans/01-implementation-steps.md`. Follows
`design/settings_window.svg` and the "Settings window" section of
`docs/general-context/02-design.md`.

## What exists already

- `ConfigStore` persists `keyterms` and `selected_provider`; `set_key()` writes to
  the OS keyring but **is never called** — keys come from `.env` only.
- All three providers accept `model` / `language` / `keyterms` in `configure()`.
- `controller.py:64` passes **only** `keyterms` — `model` and `language` are never
  passed, so every provider always falls back to its own `DEFAULT_*`.
- There is no UI to edit any of it, and no `Settings` item in the tray menu.

## Design decisions

### Option lists live on the provider classes (Open/Closed)

The settings window must not contain an `if provider == "soniox"` chain. Each
provider declares its own options as class attributes on `Provider`:

```python
display_name: str                         # "NVIDIA", not "Nvidia"
MODEL_LABEL: str                          # the one model this provider uses
LANGUAGES: list[tuple[str, str | None]]   # (label, code); None == Auto-detect
```

**Revised during implementation:** `MODEL_LABEL` started as a `MODELS` list
feeding a dropdown. After checking each provider's docs, every one has exactly
one model worth using — Groq `whisper-large-v3-turbo` (real-time oriented,
multilingual), Soniox `stt-rt-v5` (current; v4 is an alias, deprecated
2026-06-30), NVIDIA the hosted `nemotron-asr-streaming` NVCF function (not one
of the downloadable NIM containers). A one-entry dropdown is dead UI, so the
model is a read-only label. `config.json` keeps its per-provider `model` field,
always `null`, as the place a real choice would go.

The window builds each tab by iterating `PROVIDERS` and reading these. Adding a
provider stays a `providers/`-only change, as `01-features.md` requires.

### "Auto" language

`None` is the auto value end to end: stored as `null` in config.json, passed as
`language=None` to `configure()`. Groq and Soniox already treat `language=None`
as "send no language hint", so Auto works with no provider changes.

**NVIDIA is the open question** — Riva requires a `language_code`, and
`providers/nvidia.py:30` hardcodes a fallback to `en-US`. Whether the hosted
`nemotron-asr-streaming` function accepts `multi` for auto-detection is
unverified and can't be verified without a live API key. Until it is, NVIDIA's
`LANGUAGES` ships explicit codes only, with no Auto entry — the UI handles this
naturally since the list is per-provider.

### Config schema

`DEFAULTS` gains a nested `providers` block. `load()`'s merge is shallow, so add
a `provider_settings(name) -> dict` accessor rather than making callers dig:

```json
{
  "selected_provider": "groq",
  "keyterms": [],
  "providers": { "groq": { "model": null, "language": null } }
}
```

`null` means "use the provider's default" — one source of truth for defaults,
which stays in the provider module.

### API keys

Keys are never written to `config.json` and never read back into the UI.

- `ConfigStore.key_hint(provider) -> str | None` — a `gsk_••••••••3f2a` preview,
  so you can tell which key is loaded without exposing it. Masking happens in
  `ConfigStore`, so the full value never reaches the UI layer. Keys shorter than
  16 chars are fully masked, since first-4/last-4 would reveal most of them.
- `ConfigStore.has_key(provider) -> bool` — cheap "is one set at all" check.
- The **Change** button opens a small modal with a masked `Gtk.Entry`
  (`set_visibility(False)`); on OK it calls the existing `set_key()` → keyring.
- `get_key()` keeps its `.env` fallback, so nothing breaks for existing setups.
- No "show key" or "copy key" affordance, by design.

## Steps

1. **Provider option lists** — add `MODELS` / `LANGUAGES` to `Provider` and fill
   them in for all three providers.
   → verify: unit test asserts every registered provider declares both, and that
   every `LANGUAGES` entry is a `(label, code_or_None)` pair.

2. **Config schema** — add `providers` to `DEFAULTS`, add `provider_settings()`
   and `has_key()`.
   → verify: unit test round-trips per-provider settings through a tmp config dir
   and confirms an unknown/absent provider returns defaults, not a KeyError.

3. **Controller wiring** — pass `model` and `language` from
   `provider_settings()` into `configure()`.
   → verify: unit test with a fake provider asserts the configured values reach
   `configure()`, and that `null` in config arrives as `None`.

4. **`settings_window.py`** — keyterm chips (add on Enter, × removes), per-provider
   tabs via `Gtk.Notebook`, model + language `Gtk.ComboBoxText`, masked key row
   with Change, Save/Cancel. Cancel discards; Save writes config (keys are saved
   immediately by their own modal, not by Save).
   → verify: manual — open, add a keyterm, switch tabs, save, reopen, confirm it
   persisted.

5. **Tray `Settings` item** — opens the window (reuse a single instance, same
   hide-not-destroy pattern as `TranscriptWindow`).
   → verify: manual — open twice, confirm one window and no stale state.

6. **End-to-end** (the plan's stated test) — add a keyterm the provider keeps
   mis-transcribing, save, dictate the same word, confirm it's now correct.

## Out of scope

- Live NVIDIA verification (needs a real API key — carried over from Step 5).
- Editing `selected_provider` here; it stays in the tray submenu per the design.
