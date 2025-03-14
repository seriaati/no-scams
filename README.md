# no-scams

Discord bot to combat scam messages.  
Based on [this Gist](https://gist.github.com/seriaati/b38e65b8ca9257f1bec547bbd83a1a55).  
[Click to invite](https://discord.com/oauth2/authorize?client_id=790451227942060033)

## Logic

If a user sends 3 messages consecutively all in different channels AND all containing a link AND all having the same content, the bot will delete the messages and timeout the user for 15 minutes.

## Self Hosting

1. Create a [Discord application](https://discord.com/developers/applications)
1. On the **Bot** page, generate a token and save it for later
1. Enable **Message Content Intent**
1. Run the application with your bot token as the `TOKEN` environment variable
1. Invite your bot with the invite link in the logs

### Local

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
1. Clone the repository
1. Create a `.env` file:

   ```env
   TOKEN=YourDiscordBotToken.Example.SomeExampleBase64Junk
   ```

1. `uv run run.py`
