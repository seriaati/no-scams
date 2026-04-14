# Project Architecture Rules (Non-Obvious Only)

- `MessageStore` is in-memory only — no persistence; bot restart loses all tracked message history
- `HealthCheckServer` MUST be used as an async context manager alongside `bot` in the same `async with` block — it does not auto-start otherwise
- `NoScamBot` holds a single shared `MessageStore` instance (`self.store`) — all guild/user state lives here; no per-guild isolation
- Scam detection is purely reactive (`on_message`) — no background tasks, no scheduled cleanup; old messages beyond the sliding window of 3 are evicted on each new message via `remove_message()`
- `bot.delete_message()` accepts `Message` (internal dataclass), `discord.Message`, or `discord.PartialMessage` — the internal `Message` type requires a channel fetch to resolve
- Adding new scam detection heuristics requires modifying only `MessageStore.is_scam()` in [`no_scams/message_store.py`](no_scams/message_store.py) and potentially `Message.from_discord_message()` for new data fields
- `jishaku` is loaded as a dev/admin extension for live bot introspection — it is not part of scam detection logic
