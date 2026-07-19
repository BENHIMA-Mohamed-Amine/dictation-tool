# Step 5 — NVIDIA provider

**Status: done** (code + tests + tray integration verified; the manual end-to-end test needs a real NVIDIA API key the user has to supply — not yet run)

Detailed plan for [Step 5](01-implementation-steps.md): add `NvidiaProvider` (gRPC streaming via the hosted NVIDIA NIM API on build.nvidia.com), extending the `Provider` interface Groq/Soniox already implement. Registry-only wiring — no changes needed anywhere else once the class exists, per the `Provider` ABC's whole purpose.

## API verified against the real installed package (not memory)

Added `nvidia-riva-client` via `uv add nvidia-riva-client`, then introspected the installed `riva.client` module directly (`inspect.signature`, protobuf `DESCRIPTOR.fields_by_name`) to confirm the real shapes rather than guessing:

- `riva.client.Auth(uri="grpc.nvcf.nvidia.com:443", use_ssl=True, metadata_args=[["function-id", FUNCTION_ID], ["authorization", f"Bearer {api_key}"]])` — the hosted NIM endpoint, confirmed via NVIDIA's own build.nvidia.com model page and docs (two independent sources agree on `function-id: bb0837de-8c7b-481f-9ec8-ef5663e9c1fa` for the `nemotron-asr-streaming` model specifically).
- `riva.client.ASRService(auth)` — `streaming_response_generator(audio_chunks: Iterable[bytes], streaming_config) -> Generator[StreamingRecognizeResponse]`. Confirmed by signature introspection.
- `RecognitionConfig` fields (confirmed via protobuf descriptor): `encoding`, `sample_rate_hertz`, `language_code`, `max_alternatives`, `audio_channel_count`, `enable_automatic_punctuation`, no `model` field needed — the `function-id` in `Auth`'s metadata already pins the exact model deployment.
- `StreamingRecognitionConfig` fields: `config`, `interim_results`.
- `AudioEncoding.LINEAR_PCM` — confirmed enum value exists.
- `StreamingRecognizeResponse.results` → each `StreamingRecognitionResult` has `is_final`, `alternatives` (each `SpeechRecognitionAlternative` has `.transcript`) — confirmed via descriptor.
- `add_word_boosting_to_config(config, boosted_lm_words, boosted_lm_score)` — confirmed signature, used for keyterms.

## The push/pull mismatch this provider has to bridge

`streaming_response_generator` takes a *pull-style* `Iterable[bytes]` — the gRPC client reads from it as needed. Our `Provider.feed_audio(chunk)` is *push-style* (called from the audio callback thread). Bridge with a `queue.Queue`: `feed_audio()` puts chunks in; a small generator (`_audio_chunks()`) blocks on `queue.get()` and yields, returning (ending the request stream) when it gets a sentinel (`None`) that `stop()` pushes. This is the same shape as `SonioxProvider`'s listener-thread pattern, just with a queue standing in for the SDK's own event stream.

## Files

- **`providers/nvidia.py`** (new) — `NvidiaProvider(Provider)`: `name = "nvidia"`, `streaming = True`. `configure()` stores `api_key`/`language` (default `"en-US"`)/`keyterms`. `start()` builds the `Auth`/`ASRService`/`RecognitionConfig`/`StreamingRecognitionConfig` (applying word boosting if keyterms given), starts a listener thread running `streaming_response_generator` over the queue-backed generator, dispatching `is_final` results to `on_final` (appended to `_final_text_parts`, returned by `stop()`) and non-final results to `on_partial` — same shape as `SonioxProvider._listen()`. `feed_audio()` puts onto the queue. `stop()` pushes the sentinel, joins the listener thread (timeout, same defensive pattern as Soniox), returns the joined final text.
- **`providers/__init__.py`** — add `"nvidia": NvidiaProvider` to `PROVIDERS`.
- **`config.py`** — add `"nvidia": "NVIDIA_API_KEY"` to `ENV_KEY_VARS`.
- **`.env.example`** — add `NVIDIA_API_KEY=`.
- **`tray.py`** — no change needed; the provider submenu already builds itself from `PROVIDERS.keys()`.

## Tests

New `tests/step1_cli_core/test_providers_nvidia.py`, mocking `riva.client.ASRService`/`Auth` (same style as `test_providers_soniox.py` mocks `SonioxClient`):
- `NvidiaProvider` is a `Provider` subclass, `streaming is True`.
- `start()` builds an `Auth` with the hosted NIM uri and the correct `function-id`/`authorization` metadata, and a `RecognitionConfig` with the right sample rate/encoding.
- Keyterms passed to `configure()` result in `add_word_boosting_to_config` being called with those words.
- Feeding audio chunks then calling `stop()` correctly separates partial vs. final results from a fake `streaming_response_generator` response sequence, and `stop()` returns the joined final text.
- `stop()` correctly signals the audio generator to end (sentinel reaches the queue) so the listener thread doesn't hang.

## Manual verification (needs a real NVIDIA API key + desktop session)
1. Get a free API key from build.nvidia.com, set `NVIDIA_API_KEY` in `.env` (or via Settings once Step 6 exists — for now, `.env`).
2. Switch the tray's Provider submenu to "nvidia", start recording, speak, confirm partial results appear live in the popup (not just at the end), stop, confirm the Copy button has the correct final text.
