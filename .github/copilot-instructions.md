# Copilot Instructions for no-scams

## Project Overview

Discord bot that detects and prevents spam/scam messages by monitoring message patterns across channels. Core detection logic: if a user posts 3 consecutive messages in different channels with identical content (containing URLs) OR identical images, timeout the user for 15 minutes and delete the messages.

## Architecture

- **Single-file bot**: `run.py` contains the entire bot logic with `NoScamBot` class and `MessageStore` for tracking user messages
- **Utility module**: `no_scams/utils.py` has helper functions for pattern matching and image hash extraction
- **In-memory state**: `MessageStore` uses `defaultdict[tuple[guild_id, author_id], list[Message]]` to track recent messages per user per guild (no database)
- **Message dataclass**: Normalizes Discord messages into `Message` objects with `id`, `channel_id`, `content`, and `image_hashes` (frozenset)

## Key Detection Logic Flow

1. `on_message` event → `MessageStore.add_message()` stores the last 3 messages per user
2. `MessageStore.is_scam()` checks:
   - Exactly 3 messages (`MAX_MESSAGE_NUM`)
   - All in different channels (`all_different()`)
   - Either: (all contain URLs AND same content) OR (same image hashes)
3. If scam detected → delete all 3 messages, timeout user, send notification

## Critical Constants

- `MAX_MESSAGE_NUM = 3`: Number of consecutive messages to track
- `TIMEOUT_MINUTES = 15`: Timeout duration for detected scammers
- `SPECIAL_GUILD_CHANNELS = {875392637299990628: 973232047193751582}`: Guild-specific channels for timeout notifications (hardcoded mapping)
- `IMAGE_EXTENSIONS`: Validates attachment types for image hash comparison

## Development Practices

**Python version**: 3.12+ (uses `from __future__ import annotations` in all files)

**Code style** (enforced by ruff):
- Line length: 100 characters
- Use type hints everywhere (ANN rules enabled)
- Required import: `from __future__ import annotations` at top of every file
- No trailing commas in collections/function calls (`skip-magic-trailing-comma = true`)
- Pyright type checking on "standard" mode

**Running the bot**:
- Development: `uv run run.py` (uv manages dependencies from `pyproject.toml`)
- Production: PM2 with `.venv/bin/python -OO run.py` (see `pm2.json`)
- Environment: Requires `TOKEN` env var (Discord bot token), load from `.env` via `python-dotenv`

**Dependencies**:
- `discord.py[speed]`: Discord API client with performance extras
- `imagehash`: Perceptual image hashing for duplicate detection
- `Pillow`: Image processing for hash generation

## Common Patterns

**Error suppression**: Uses `contextlib.suppress(discord.NotFound, discord.Forbidden)` when deleting messages or timing out users to handle missing permissions gracefully

**Image hash comparison**: 
- `imagehash.average_hash()` generates perceptual hashes from PIL Images
- Store as `frozenset[ImageHash]` for set comparison in `Message.image_hashes`
- Only process attachments with image MIME types and valid extensions

**Channel type guards**: Always check channel types before operations (e.g., `isinstance(channel, discord.TextChannel | discord.Thread | discord.VoiceChannel)`) since `get_channel()` can return forum/category channels

**Logging**: Use `logging.getLogger("discord.bot")` for all log statements, DEBUG env var enables verbose scam detection logging

## Testing Scam Detection

Set `DEBUG=1` environment variable to see boolean checks in logs:
```
same_content, different_channels, all_contain_url, same_images
```

Manual test: Create a bot user, send 3 messages with same URL content in 3 different channels rapidly.

## Key Files

- `run.py`: Complete bot implementation (Message, MessageStore, NoScamBot classes)
- `no_scams/utils.py`: Helper functions (url detection, image hashing, list comparison utilities)
- `pyproject.toml`: Dependencies and type checker config
- `ruff.toml`: Code style rules (100 char lines, PY312 target, extensive linter rules)
