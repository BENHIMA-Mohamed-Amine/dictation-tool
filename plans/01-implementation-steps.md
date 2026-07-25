# Implementation steps

**Status: approved**

Each step below is a complete, end-to-end testable slice of the app — not just a file or a layer. Nothing is "half-wired." Every step ends with something you can actually run and verify before moving to the next.

## Step 1 — CLI dictation core ✅ done (see `plans/done/02-step1-cli-core.md`)
**Files:** `config.py`, `providers/base.py`, `providers/__init__.py`, `providers/groq.py`, `providers/soniox.py`, `audio.py`, `controller.py`
**What it does:** record mic audio, send to either Groq (batch) or Soniox (streaming), print the transcript to the terminal. Both providers implemented here on purpose — proves the `Provider` interface works for both the batch and streaming shape early, before any UI is built on top of it. No tray, no auto-type, no settings UI — a plain script.
**End-to-end test:** run the script with Groq selected, speak a sentence, see the correct text printed; repeat with Soniox selected, confirm partials print live to the terminal as you speak.

## Step 2 — Auto-type output ✅ done, later removed (see `plans/done/03-step2-auto-type.md` and `plans/done/08-remove-auto-output.md`)
**Files:** added `output.py`; `controller.py` typed instead of printing
**What it did:** same flow as step 1, but the final transcript was typed into whichever window was focused when recording started, via `xdotool`. **Removed** after Step 3 shipped: `xdotool` can't act on native Wayland windows at all, and the clipboard-with-notification fallback that replaced it still had a confusing multi-second lag before the clipboard was actually ready. `output.py` is deleted; the popup's Copy button (Step 3) is now the only output mechanism.

## Step 3 — Tray app ✅ done (see `plans/done/04-step3-tray-app.md` and `plans/done/05-step3-fixes-transcript-window.md`)
**Files:** add `tray.py`, `transcript_window.py`, `main.py` (App orchestrator)
**What it does:** replaces the manual script run with the real UI — click the tray mic icon to start/stop, see the transcript in a popup as it comes in. Output is the popup's Copy button (auto-typing was removed, see Step 2).
**End-to-end test:** click the tray icon, speak, watch the popup update, use the Copy button, confirm the clipboard matches.

## Step 4 — Global hotkey ✅ done, later removed (see `plans/done/09-step4-global-hotkey.md` and `plans/done/10-remove-global-hotkey.md`)
**Files:** added `hotkey_daemon.py`, `ControlSocket` in `main.py`
**What it did:** same start/stop behavior as the tray click, triggered by a keyboard shortcut via a Unix socket, bound through GNOME Custom Shortcuts. The socket mechanism itself worked (verified directly), but the GNOME keybinding never actually fired the command when pressed — a GNOME/environment integration issue, not worth continuing to debug for a second trigger on a feature that already works from the tray. **Removed**: `hotkey_daemon.py` deleted, `ControlSocket` removed from `main.py`, the GNOME custom keybinding unbound. Tray click remains the only trigger.

## Step 5 — Remaining provider (NVIDIA) ✅ done (see `plans/done/11-step5-nvidia-provider.md`) — manual live test still pending a real NVIDIA API key
**Files:** add `providers/nvidia.py`
**What it does:** same tray/hotkey flow, extended to the third provider (gRPC streaming). Groq and Soniox already exist from step 1 — this step just adds NVIDIA to the registry and wires provider switching into the tray submenu for all three.
**End-to-end test:** switch between Groq, Soniox, and NVIDIA from the tray, confirm each transcribes correctly (partials live for Soniox/NVIDIA, single result for Groq).

## Step 6 — Settings window ✅ implemented (see `plans/12-step6-settings-window.md`) — manual end-to-end test pending
**Files:** add `settings_window.py`
**What it does:** replaces any hardcoded config/API keys with the real settings UI — global keyterms list, per-provider model/key/language, all persisted via `ConfigStore` + `keyring`.
**End-to-end test:** add a keyterm the current provider keeps mis-transcribing, save, dictate the same word again, confirm it's now correct.

---

Each step gets its own commit. Move this file to `plans/done/` once step 6 is verified and the whole app matches the design docs in `docs/general-context/`.
