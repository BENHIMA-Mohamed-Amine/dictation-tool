# Design

## Tray menu (click centered mic icon in top bar)
- Top row: centered mic icon only — click to start recording (icon turns red/active while recording), click again to stop.
- **Provider**: opens a submenu (Soniox / NVIDIA / Groq) — radio-style select, one checked at a time.
- **Settings**: opens the settings window.
- **Quit**.

## Settings window
- **Keyterms / vocabulary boost**: one global tag list (add term, press Enter; removable chips) at the top — shared across all providers, feeds each provider's keyword-boosting config.
- Below that, per-provider tabs (Soniox / NVIDIA / Groq), each with: Model (read-only label — each provider has exactly one model worth using, so there's nothing to pick), API key (first/last four characters with the middle masked, e.g. `gsk_••••••••3f2a`, + Change button opening a secure prompt — enough to tell two keys apart, never the full value), Language (dropdown, defaulting to Auto-detect where the provider supports it).
- No output-mode setting to speak of — auto-type/clipboard-on-stop was tried and removed (didn't work reliably on Wayland, timing was confusing). Output is manual: the popup's Copy button.
- Save / Cancel at the bottom.

## Transcript popup
- Appears when recording starts.
- Shows live/partial text as it streams in (or rolling-batch updates for Groq).
- Copy button — the only way to get the transcript out; reads the buffer directly at click time, so it's always in sync with what's shown.
- Accumulates across Start/Stop cycles until closed; closing clears it.
