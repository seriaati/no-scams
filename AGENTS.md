# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Stack
- Python 3.12, discord.py, uv package manager
- No test suite exists — no test commands to run
- Deployed via pm2 (uses `.venv/bin/python -OO run.py`) or Docker

## Commands
```bash
uv run python run.py          # run the bot locally (requires TOKEN env var)
uv run ruff check --fix .     # lint with autofix
uv run ruff format .          # format
```

## Architecture
- [`run.py`](run.py) — entry point; `NoScamBot` subclasses `commands.Bot`, loads `jishaku` extension
- [`no_scams/message_store.py`](no_scams/message_store.py) — `MessageStore` keyed by `(guild_id, author_id)` tuple; sliding window of last `MAX_MESSAGE_NUM` (3) messages per user per guild
- [`no_scams/health.py`](no_scams/health.py) — aiohttp server on `127.0.0.1:8080/health`, used as async context manager alongside `bot`
- [`no_scams/constants.py`](no_scams/constants.py) — `SPECIAL_GUILD_CHANNELS` maps guild IDs to specific notification channel IDs (hardcoded)

## Scam Detection Logic
A message is flagged as scam when sent across **different channels** within `CONSECUTIVE_WINDOW_MINUTES` (2 min) AND one of:
- Same text content containing a URL
- Same image hash (perceptual hash via `imagehash`)
- All messages have images and no text

After detection: scam messages are deleted, author is timed out for `TIMEOUT_MINUTES` (15), and a notification is sent to `SPECIAL_GUILD_CHANNELS` if configured, otherwise to the triggering channel.

## Code Style
- `future-annotations = true` — always use `from __future__ import annotations` style (PEP 563)
- `skip-magic-trailing-comma = true` — ruff format ignores trailing commas for line-break decisions
- `split-on-trailing-comma = false` — isort does not split on trailing commas
- Line length 100, Google docstring convention
- All functions must be annotated (ANN rules enforced); `ANN401` (Any) is allowed
- Loggers use `logging.getLogger("discord.bot")` hierarchy (prefixed with `discord.`)
- `noqa: ANN001` used in `__aexit__` for untyped exception params — acceptable pattern
