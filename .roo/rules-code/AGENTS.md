# Project Coding Rules (Non-Obvious Only)

- `from __future__ import annotations` is required in every file — ruff enforces `future-annotations = true`
- `image_hashes` stored as `frozenset[imagehash.ImageHash]` on `Message` dataclass — must remain hashable for set comparisons in scam detection
- `MessageStore._messages` uses `defaultdict[tuple[int, int], list[Message]]` — key is `(guild_id, author_id)`, not a string
- After scam detection, call `store.clear_messages(guild_id, author_id)` — store is NOT auto-cleared
- `HealthCheckServer` binds only to `127.0.0.1:8080` — not `0.0.0.0`; Docker exposes port 8080 externally
- `noqa: ANN001` is the accepted pattern for `__aexit__` exception params — do not add type annotations there
- `ruff.toml` has `preview = true` — some rules are preview-only; always run `uv run ruff check --fix` after edits
- pm2 runs with `-OO` flag (strips docstrings and assertions) — do not rely on assertions or docstrings at runtime
