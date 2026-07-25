# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Execute Explicit Instructions

**When the user gives a clear, actionable instruction, do it. Don't substitute your own process step.**

- An explicit instruction ("create the folder", "do X now") is not a request for re-confirmation, even if a plan or discussion preceded it.
- Don't insert an extra approval/planning/confirmation step out of habit when the ask was already unambiguous.
- Reserve confirmation steps (plan mode, clarifying questions) for genuine ambiguity, multiple valid approaches, or newly-introduced risk — not as a default reflex after any prior discussion.
- If you're unsure whether an instruction is "confirmed enough" to act on directly, that uncertainty itself should be named and asked about - don't silently fall back to a heavier process instead.
- This does not mean comply blindly. If an instruction is technically unsound, a poor fit for the problem, or likely to cause pain later (see Rule 1: Think Before Coding), say so BEFORE starting work — not after. Claude has the right, and the obligation, to push back with the specific reason. Push back once, clearly, then follow the user's call once they've heard it.

## 6. Plan Files for Big Features

**Big features get a tracked plan file. Small fixes don't.**

- For any big feature (new capability, meaningful architectural work, multi-file change), create a markdown plan file inside the project's root-level `plans/` folder before implementing.
- Each plan file has a status, tracked at the top of the file: `proposed` → `approved` → `done`, or `deferred` if paused/shelved.
- When a plan reaches `done`, move its file into a `plans/done/` subfolder — the plan record stays, but out of the active list.
- Small bug fixes and small modifications do NOT need a plan file — this workflow is only for big features. Use judgment; don't create ceremony for a one-line fix.

## 7. Project Structure (Living Section)

**Keep the section below current as the project grows. Additive only — never wipe it.**

- As new files/folders are created, add an entry here with a short one-line description of what it's for.
- If a file's role changes, update its description in place rather than leaving it stale.
- Don't remove an entry just because you're unsure if it's still accurate — check first.

## Project Structure

```
dictation-tool/
├── design/                    # UI mockups for the tray menu and settings window
├── plans/                     # tracked plan files for big features (status: proposed/approved/done/deferred)
│   └── done/                  # completed plan files, moved here once a plan's status reaches `done`
├── docs/
│   ├── adding-a-provider.md   # how-to for adding a new STT backend (the Provider contract, registry, keys, tests)
│   └── general-context/       # background reference docs (general plan, features, design, class design) — not tracked plan files
├── providers/
│   ├── base.py                # Provider ABC — the interface every STT backend implements, plus the settings-UI metadata each one declares (display_name, MODEL_LABEL, LANGUAGES) and the shared ISO_639_1_LANGUAGES list
│   ├── groq.py                 # GroqProvider — batch REST transcription via Groq's Whisper endpoint
│   ├── soniox.py                # SonioxProvider — real-time streaming via the official Soniox SDK
│   ├── nvidia.py                # NvidiaProvider — gRPC streaming via nvidia-riva-client against the hosted NIM API (nemotron-asr-streaming)
│   └── __init__.py               # PROVIDERS registry dict, the extension point for adding providers
├── tests/                     # automated tests, one subfolder per build step (e.g. step1_cli_core/), no real mic/network needed
├── audio.py                   # AudioRecorder — mic capture via sounddevice
├── config.py                  # ConfigStore — config.json (selected_provider, keyterms, per-provider model/language) + keyring-backed API key storage. `null` for model/language means "use the provider module's default"
├── settings_window.py         # SettingsWindow — global keyterm chips + a tab per registered provider (model shown read-only, API key, language). Tabs are built from each provider class's MODEL_LABEL/LANGUAGES/display_name, so adding a provider needs no change here. Keys go straight to the keyring from their own masked dialog, not on Save
├── controller.py                # DictationController — start()/stop()/toggle() + record_once() CLI wrapper. No auto-output: callers read the transcript from stop()'s return value or the popup.
├── tray.py                    # TrayIcon — AppIndicator3 (AyatanaAppIndicator3) tray menu: toggle, provider submenu, settings, quit. Note: the menu closes on every click (dbusmenu behavior, not fixable), which is why the everyday Start/Stop control also lives in the transcript window
├── transcript_window.py       # TranscriptWindow — GTK window: editable transcript + Start/Stop, Copy, Clear buttons. Shown at launch; the Start/Stop button here is the everyday control (tray menus close on every click). A GTK mark splits settled text (user-editable) from the live partial tail (the only part rewritten). Copy is the only way to get text out (auto-type/clipboard-on-stop was tried and removed — see plans/done/08-remove-auto-output.md)
├── main.py                    # App orchestrator — wires ConfigStore, DictationController, TrayIcon, TranscriptWindow, SettingsWindow; runs Gtk.main(). Tray click is the only trigger (a ControlSocket/hotkey_daemon.py global-hotkey path was tried and removed — GNOME keybinding never fired the command — see plans/done/10-remove-global-hotkey.md)
├── dictation                  # `dictation start|stop|status` launcher — runs main.py detached via .venv/bin/python, pidfile in $XDG_RUNTIME_DIR. Symlink it into ~/.local/bin
├── pyproject.toml             # uv-managed project config
├── .env                       # local secrets (GROQ_API_KEY, SONIOX_API_KEY) — gitignored
├── .env.example                # template for .env, committed
└── README.md                  # setup instructions: uv sync, required OS packages (xdotool, xclip, GTK/AppIndicator dev headers), .env setup
```

## 8. Response Style

**Bullet points. Clear. Concise. Fast to read.**

- Default to bullet points over prose paragraphs.
- Keep each point short — no essays, no padding.
- Answers should be scannable in a few seconds, not read top to bottom like an article.

## 9. Code Quality

**SOLID, clear, idiomatic. One source of truth per fact.**

- Follow SOLID principles — in particular **Open/Closed**: code should be open for extension, closed for modification. New behavior (a new provider, a new format, a new rule) should be addable by adding new code, not by editing existing working code. This is why we use registries/interfaces at extension points instead of `if/elif` chains on type.
- Code should be clear and idiomatic for the language it's written in — follow that language's established conventions and best practices, not patterns borrowed from a different ecosystem.
- **Single source of truth**: any given fact, config value, or piece of logic lives in exactly one place. If updating something requires editing it in more than one file, that's a design smell — refactor so there's one place to change it.
- **Dependencies**: always use `uv add <package>` (or `uv add --dev <package>` for dev-only deps) to add a dependency. Never hand-edit `pyproject.toml`'s `dependencies` list directly — `uv add` keeps `pyproject.toml` and `uv.lock` in sync, which is the single source of truth for this project's dependency versions.
- This section works together with Rule 2 (Simplicity First) — SOLID and DRY are not a license to add abstraction speculatively. Apply them where a real second case, a real extension point, or a real duplication already exists, not in anticipation of one.

## 10. The Meta-Principle

**An agent that understands its own token budget is an agent that never gets stuck.**

Instead of running into context limits unexpectedly, it:
1. Estimates before starting.
2. Checkpoints proactively.
3. Spawns subagents when the task is too large.
4. Reports progress in terms humans can understand: "I'm at 60% context, 40% task complete, spawning 2 subagents for the remaining work."

This is what separates agents that can run autonomously for hours from agents that silently degrade and fail.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
