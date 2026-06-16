# Privacy Policy

_Last updated: 2026-06-16_

This Privacy Policy describes how the **no-scams** Discord bot ("the bot", "we") handles
data. The bot is an automated moderation tool that detects and removes coordinated
spam/scam messages in Discord servers. Its source code is publicly available at
https://github.com/seriaati/no-scams.

## What data the bot accesses

To detect scam campaigns, the bot reads messages sent in servers where it is present.
For each message it temporarily examines:

- The message text content.
- Image attachments (to compute a perceptual hash for comparison).
- The message's channel ID, author ID, server ID, message ID, and timestamp.

The bot requires Discord's **Message Content** intent to read message text, because its
detection logic compares the text and images of a user's recent messages to identify
spam sent across multiple channels.

## How the data is used

The data is used for one purpose only: real-time detection of spam/scam behavior. A user
is flagged when they send 3 messages in different channels within 2 minutes that are
identical in text, share the same image(s), or are all image-only. When this happens, the
bot deletes those messages and times the user out for 15 minutes.

The data is **not** used for analytics, profiling, advertising, or training machine
learning or AI models.

## How the data is stored

- Message data is held **only in volatile memory (RAM)** during analysis.
- At most the **3 most recent messages** per user per server are kept at any time.
- This data is **cleared immediately** after a moderation action and is continuously
  discarded as new messages replace old ones.
- Message content is **never written to disk, a database, logs, or any external service**.
- No data is stored off-platform (outside of Discord).

## Data sharing

We do not sell, share, or transmit any message data to third parties.

## Data retention

The bot retains no message content beyond the brief in-memory window described above.
There is no persistent storage and therefore no long-term retention.

## User rights

Because the bot keeps no persistent records of any user, there is no stored personal data
to access, export, or delete. Server administrators control whether the bot is present in
their server; removing the bot stops all data access immediately.

## Children's privacy

The bot is intended for use within Discord and is subject to Discord's own age
requirements. We do not knowingly collect data from children in violation of those
requirements.

## Changes to this policy

This policy may be updated over time. Changes will be reflected in this file with an
updated date.

## Contact

For questions about this policy, open an issue at
https://github.com/seriaati/no-scams/issues.
