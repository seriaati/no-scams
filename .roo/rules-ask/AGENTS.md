# Project Documentation Rules (Non-Obvious Only)

- Scam detection requires exactly `MAX_MESSAGE_NUM` (3) messages before triggering — fewer messages are never flagged regardless of content
- `SPECIAL_GUILD_CHANNELS` in [`no_scams/constants.py`](no_scams/constants.py) hardcodes guild→channel mappings; there is no config file or database for this
- `all_same()` in [`no_scams/utils.py`](no_scams/utils.py) returns `False` for single-element or empty lists — intentional, not a bug
- `all_different()` returns `True` for single-element lists — scam detection requires all 3 messages in different channels
- Image hashing uses perceptual hash (`imagehash.average_hash`) not exact hash — near-duplicate images are caught
- Discord invite URLs are detected separately from generic URLs via `DISCORD_INVITE` regex in [`no_scams/constants.py`](no_scams/constants.py)
