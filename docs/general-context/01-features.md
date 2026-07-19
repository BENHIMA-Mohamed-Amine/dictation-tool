# Features

- Ubuntu top-bar tray icon (mic), click to start/stop recording, icon reflects recording state.
- Global keyboard shortcut to start/stop recording, bound via GNOME Custom Shortcuts, without needing to click the tray icon.
- Choice of STT provider (Soniox, NVIDIA, Groq to start), selected from a submenu in the tray, one active at a time.
- Pluggable provider architecture — adding a new provider later requires no changes outside the `providers/` folder.
- Per-provider configuration: model, API key, language.
- Global keyterms / vocabulary boost list, shared across all providers, to fix words the STT keeps missing.
- Live transcript display while speaking (true streaming for Soniox/NVIDIA, rolling-batch updates for Groq).
- Automatic typing of the final transcript into whatever window was focused before recording started.
- Copy button on the transcript popup for manual correction/copy.
- API keys stored securely via the OS keyring (GNOME Keyring), never in plaintext config.
