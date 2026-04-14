import asyncio
import contextlib
import datetime
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from no_scams.constants import SPECIAL_GUILD_CHANNELS, TIMEOUT_MINUTES
from no_scams.health import HealthCheckServer
from no_scams.message_store import Message, MessageStore

logger = logging.getLogger("discord.bot")

intents = discord.Intents.default()
intents.message_content = True
permissions = discord.Permissions(
    moderate_members=True, manage_messages=True, read_message_history=True, send_messages=True
)
allowed_mentions = discord.AllowedMentions(everyone=False, roles=False, users=True)


class NoScamBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(commands.when_mentioned, intents=intents)
        self.store = MessageStore()
        self.actioned_users: set[tuple[int, int]] = set()
        self.user: discord.ClientUser

    async def delete_message(
        self, message: Message | discord.Message | discord.PartialMessage
    ) -> None:
        if isinstance(message, Message):
            channel = bot.get_channel(message.channel_id) or await bot.fetch_channel(
                message.channel_id
            )
            if isinstance(
                channel, discord.ForumChannel | discord.CategoryChannel | discord.abc.PrivateChannel
            ):
                return

            message = channel.get_partial_message(message.id)

        try:
            logger.info("Deleting message %s in %r", message.id, message.guild)
            await message.delete()
        except discord.NotFound:
            logger.warning("Message %s in %r was already deleted", message.id, message.guild)
        except discord.Forbidden:
            logger.warning("No permission to delete message %s in %r", message.id, message.guild)
        except discord.HTTPException as e:
            logger.warning(
                "Failed to delete message %s in %r: %s (code %s)",
                message.id,
                message.guild,
                e.text,
                e.code,
            )
        except Exception:
            logger.exception(
                "Unexpected error deleting message %s in %r", message.id, message.guild
            )

    async def timeout_member(self, message: discord.Message) -> None:
        if not isinstance(message.author, discord.Member):
            return
        try:
            logger.info("Timing out %r", message.author)
            await message.author.timeout(
                datetime.timedelta(minutes=TIMEOUT_MINUTES), reason="Sending scam messages"
            )
        except discord.NotFound:
            logger.warning("Cannot find %r to timeout in %r", message.author, message.guild)
        except discord.Forbidden:
            logger.warning("Failed to timeout %r", message.author)
        except discord.HTTPException as e:
            logger.warning("Failed to timeout %r: %s (code %s)", message.author, e.text, e.code)
        except Exception:
            logger.exception("Unexpected error timing out %r", message.author)
        else:
            logger.info("Timed out %r", message.author)
            await self._send_timeout_notification(message)

    async def _send_timeout_notification(self, message: discord.Message) -> None:
        assert message.guild is not None
        timeout_msg = f"Timed out {message.author.mention} for {TIMEOUT_MINUTES} minutes for sending scam messages\n"
        if channel_id := SPECIAL_GUILD_CHANNELS.get(message.guild.id):
            special_channel = message.guild.get_channel(
                channel_id
            ) or await message.guild.fetch_channel(channel_id)
            if isinstance(
                special_channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)
            ):
                await special_channel.send(
                    timeout_msg
                    + f"\nThe message that triggered the timeout was:\n{message.content}"
                )
        else:
            await message.channel.send(timeout_msg)

    async def setup_hook(self) -> None:
        await self.load_extension("jishaku")

    async def on_ready(self) -> None:
        logger.info("Invite: %s", discord.utils.oauth_url(self.user.id, permissions=permissions))


bot = NoScamBot()


@bot.event
async def on_message(message: discord.Message) -> None:
    # Skip bot messages, DMs, and webhooks
    if message.author.bot or message.guild is None or message.webhook_id is not None:
        return

    key = (message.guild.id, message.author.id)

    if key in bot.actioned_users:
        logger.info(
            "Deleting message from already-actioned user %r in %r", message.author, message.guild
        )
        await bot.delete_message(message)
        return

    store = bot.store
    await store.add_message(message)

    if store.is_scam(message):
        logger.info(
            "Scam detected from %r in %r: %r", message.author, message.guild, message.content
        )

        bot.actioned_users.add(key)
        try:
            scam_messages = store.get_scam_messages(message)
            for scam_message in scam_messages:
                await bot.delete_message(scam_message)
            await bot.timeout_member(message)
        finally:
            store.clear_messages(*key)
            bot.actioned_users.discard(key)

    await bot.process_commands(message)


async def main() -> None:
    load_dotenv()
    discord.utils.setup_logging(level=logging.INFO)
    async with bot, HealthCheckServer(bot):
        await bot.start(os.environ["TOKEN"])


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
        asyncio.run(main())
