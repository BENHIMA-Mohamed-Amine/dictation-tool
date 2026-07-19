# Step 1 — CLI dictation core

**Status: done** — verified end-to-end with real mic + real Groq/Soniox keys (2026-07-18). Both providers transcribe correctly; the initial hang-on-stop and `<fin>` token leak found during manual testing were fixed and re-verified. One known low-severity cosmetic issue remains: an occasional missing space at a finalize boundary when Soniox revises a self-corrected phrase — traced to the streaming ASR's own token revision, not our code; left as-is, not a blocker.

Detailed plan for [Step 1](01-implementation-steps.md) of the overall build: record mic audio, send it to either Groq (batch) or Soniox (streaming), print the transcript. No tray, no auto-type, no settings UI — a plain script, but a real end-to-end vertical slice. Both providers are built now, on purpose, to prove the `Provider` interface holds for both the batch and streaming shape before any UI is layered on top.

## Files

- **`config.py`** — `ConfigStore` class. `load()` / `save()` for `~/.config/dictation-tool/config.json`. For step 1, holds just `selected_provider` (defaults to `"groq"`) and `keyterms: list[str]` (defaults to `[]`). Also wraps `keyring`: `get_key(provider)` / `set_key(provider, value)`. For step 1, each provider's key is read from an env var (`GROQ_API_KEY`, `SONIOX_API_KEY`) if `keyring` has nothing set yet (so the CLI is runnable immediately without opening a settings UI that doesn't exist yet).
- **`providers/base.py`** — `Provider` ABC: `name: str`, `streaming: bool`, `configure(api_key, model, language, keyterms)`, `start(on_partial, on_final)`, `feed_audio(chunk: bytes)`, `stop() -> str`.
- **`providers/groq.py`** — `GroqProvider(Provider)`. `streaming = False`. `feed_audio` appends to an internal `bytearray` buffer. `stop()` writes the buffer to a temp WAV, POSTs it to `https://api.groq.com/openai/v1/audio/transcriptions` via `requests`, returns the transcript text. `configure()` stores `api_key`, `model` (default `whisper-large-v3-turbo`), `language`, and folds `keyterms` into the `prompt` field (comma-joined).
- **`providers/soniox.py`** — `SonioxProvider(Provider)`. `streaming = True`. Uses the official Soniox Python SDK (`SonioxClient`, `RealtimeSTTConfig`). `start(on_partial, on_final)` opens the real-time session (`model="stt-rt-v5"`, `audio_format="pcm_s16le"`, keyterms passed via `context=StructuredContext(terms=keyterms)`) and starts a background thread reading `session.receive_events()`, dispatching to the callbacks. `feed_audio(chunk)` calls `session.send_byte_chunk(chunk)`. `stop()` calls `session.finalize()`, joins the listener thread, closes the session, and returns the accumulated final transcript.
- **`providers/__init__.py`** — `PROVIDERS = {"groq": GroqProvider, "soniox": SonioxProvider}` registry.
- **`audio.py`** — `AudioRecorder` class wrapping `sounddevice`. `start(on_chunk: Callable[[bytes], None])` opens an input stream, calling `on_chunk` with raw PCM frames as they arrive. `stop()` closes the stream.
- **`controller.py`** — `DictationController`. For step 1: `record_once() -> str` — creates the configured `Provider`, calls `provider.start(on_partial=print, on_final=None)`, starts `AudioRecorder` wired to `provider.feed_audio`, blocks until Enter is pressed (simplest possible "stop" trigger for a CLI-only step — no tray/hotkey exists yet), stops the recorder, calls `provider.stop()`, returns the text. Works identically regardless of which provider is selected — that's the point of the shared interface.
- **`__main__.py`** (or a `if __name__ == "__main__"` block in `controller.py`) — CLI entry: reads `--provider groq|soniox` (defaults to `ConfigStore`'s `selected_provider`), calls `record_once()`, prints the final result.

## Out of scope for step 1 (comes later)
Auto-type (step 2), tray (step 3), hotkey (step 4), NVIDIA provider (step 5), settings UI (step 6).

## Tests

New folder: `tests/step1_cli_core/`, using `pytest` (added to `pyproject.toml` as a dev dependency).

- **`tests/step1_cli_core/test_config.py`**
  - Round-trip: `ConfigStore.save()` then a fresh `ConfigStore.load()` (using a `tmp_path`-based config dir, not the real `~/.config`) returns the same values.
  - Defaults: loading with no existing config file returns `selected_provider == "groq"` and `keyterms == []`.
- **`tests/step1_cli_core/test_providers_groq.py`**
  - `GroqProvider` is a `Provider` (interface conformance).
  - `configure()` correctly builds the `prompt` string from a keyterms list.
  - `stop()` calls `requests.post` with the right URL, headers, and file — verified with `unittest.mock.patch`, no real network call, and returns the mocked response's transcript text.
- **`tests/step1_cli_core/test_providers_soniox.py`**
  - `SonioxProvider` is a `Provider` (interface conformance), `streaming is True`.
  - `configure()` correctly builds the SDK's context/keyterms config from a keyterms list.
  - `start()`/`feed_audio()`/`stop()` against a mocked Soniox SDK client (no real websocket) — confirms `feed_audio` forwards chunks to the mocked session, and that mocked partial/final events reach the `on_partial`/`on_final` callbacks and get accumulated into `stop()`'s return value.
- **`tests/step1_cli_core/test_controller.py`**
  - `record_once()` with a fake `Provider` (records call order) and a fake `AudioRecorder` (immediately feeds one dummy chunk) confirms the sequence: `configure` → `start` → `feed_audio` → `stop`, and that the returned text matches the fake provider's `stop()` return value.
  - Run this same test parametrized against both a fake batch-style and fake streaming-style provider, to confirm the controller doesn't need to know which kind it's talking to.

## Manual verification (not automated — needs a real mic/network)
- Run the CLI entry point with `--provider groq`, speak a sentence, press Enter, confirm the printed transcript is correct.
- Run again with `--provider soniox`, confirm partial words print live to the terminal while speaking, and the final transcript is correct.
- Record to a WAV first via a small `audio.py` smoke check (record 3s, save, play back) to confirm mic capture itself works before wiring it to either provider.

## Dependencies
Installed via `uv add` (never hand-edited into `pyproject.toml`):
```
uv add sounddevice requests keyring soniox
uv add --dev pytest
```
