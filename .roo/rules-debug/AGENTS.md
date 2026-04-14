# Project Debug Rules (Non-Obvious Only)

- Scam detection debug logs are at `logging.DEBUG` level via `logger.debug(...)` in [`no_scams/message_store.py`](no_scams/message_store.py) — not visible at default `INFO` level; change `discord.utils.setup_logging(level=logging.DEBUG)` in [`run.py`](run.py) to see them
- `HealthCheckServer` returns 503 if `bot.is_ready()` is False or `bot.is_closed()` is True — useful for diagnosing startup failures
- `MessageStore` silently drops messages if `message.guild` is `None` (DMs) — not an error
- `bot.delete_message()` silently swallows `discord.NotFound` and `discord.Forbidden` — check logs for warnings, not exceptions
- pm2 and Docker both run with `-OO` — assertions are stripped; never use `assert` for logic guards
- `TOKEN` env var must be set; loaded via `python-dotenv` from `.env` file at startup in [`run.py`](run.py)
