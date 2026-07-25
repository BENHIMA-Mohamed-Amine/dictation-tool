---
description: Scaffold a new STT provider (usage: /add-provider <name> <docs-url>)
---

Add a new STT provider to this project: **$ARGUMENTS**

Follow @docs/adding-a-provider.md exactly. Read an existing provider
(`providers/groq.py` for batch, `providers/soniox.py` for streaming) and match
whichever shape the new API has.

Before writing code:
- Read the provider's API docs (fetch the URL if one was given, otherwise search
  for the current streaming/batch STT endpoint and model id).
- Report the model id you picked and why, plus whether it's streaming or batch.
  Do not guess a model id — verify it exists.

Then do the work end to end: the provider module, the `PROVIDERS` entry, the
`.env.example` variable, `uv add` for any SDK, a hardware-free test, and the
`CLAUDE.md` project-structure entry.

Finish with `uv run pytest -q` and report the result. Do not commit.
