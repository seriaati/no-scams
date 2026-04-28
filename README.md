# no-scams

Discord bot to combat scam messages.  
Based on [this Gist](https://gist.github.com/seriaati/b38e65b8ca9257f1bec547bbd83a1a55).  
[Click to invite](https://discord.com/oauth2/authorize?client_id=790451227942060033)

## Logic

1. The user sends 3 messages consecutively.
2. All messages are in different channels.
3. The 3 messages are sent within 2 minutes.
4. At least one of these is true:

- All messages have the same content.
- All messages have the same image attachment hash(es).
- All messages have image attachments and no text content.

If all of the above conditions are met, the bot deletes the messages and timeouts the user for 15 minutes.

## Self Hosting

1. Create a [Discord application](https://discord.com/developers/applications)
1. On the **Bot** page, generate a token and save it for later
1. Enable **Message Content Intent**
1. Run the application with your bot token as the `TOKEN` environment variable
1. Invite your bot with the invite link in the logs

### Docker (Recommended)

Using the pre-built image from GitHub Container Registry:

```bash
docker run -d \
  --name no-scams-bot \
  --restart unless-stopped \
  -e TOKEN=YourDiscordBotToken.Example.SomeExampleBase64Junk \
  ghcr.io/seriaati/no-scams:latest
```

Or using Docker Compose:

```yaml
services:
  bot:
    image: ghcr.io/seriaati/no-scams:latest
    container_name: no-scams-bot
    restart: unless-stopped
    environment:
      TOKEN: YourDiscordBotToken.Example.SomeExampleBase64Junk
```

### Local

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
1. Clone the repository
1. Create a `.env` file:

   ```env
   TOKEN=YourDiscordBotToken.Example.SomeExampleBase64Junk
   ```

1. `uv run run.py`
