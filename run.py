from collections import defaultdict
import contextlib
from dataclasses import dataclass
import datetime
import logging
import os
import re
from typing import Any
from discord.ext import commands
import discord
from dotenv import load_dotenv

MAX_MESSAGE_NUM = 3
TIMEOUT_MINUTES = 15

logger = logging.getLogger("discord")


@dataclass(kw_only=True)
class Message:
    id: int
    channel_id: int
    content: str


class MessageStore:
    def __init__(self) -> None:
        self._messages: defaultdict[tuple[int, int], list[Message]] = defaultdict(list)
        """(guild ID, author ID) -> list of messages"""

    @staticmethod
    def contains_url(content: str) -> bool:
        return re.search(r"https?://\S+", content) is not None

    @staticmethod
    def all_same(lst: list[Any]) -> bool:
        if not lst or len(lst) == 1:
            return False
        return all(x == lst[0] for x in lst)

    @staticmethod
    def all_different(lst: list[Any]) -> bool:
        if not lst or len(lst) == 1:
            return True
        return len(set(lst)) == len(lst)

    def add_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return

        self._messages[message.guild.id, message.author.id].append(
            Message(
                id=message.id,
                channel_id=message.channel.id,
                content=message.content,
            )
        )
        self.remove_message(message.guild.id, message.author.id)

    def remove_message(self, guild_id: int, author_id: int) -> None:
        if len(self._messages[guild_id, author_id]) > MAX_MESSAGE_NUM:
            self._messages[guild_id, author_id].pop(0)

    def clear_messages(self, guild_id: int, author_id: int) -> None:
        self._messages[guild_id, author_id].clear()

    def get_scam_messages(self, message: discord.Message) -> list[Message]:
        if message.guild is None:
            return []
        return self._messages[message.guild.id, message.author.id]

    def is_scam(self, message: discord.Message) -> bool:
        messages = self.get_scam_messages(message)
        if len(messages) < MAX_MESSAGE_NUM:
            return False

        # All messages have the same content, all in different channels, and all contain URLs
        return (
            self.all_same([message.content for message in messages])
            and self.all_different([message.channel_id for message in messages])
            and all(self.contains_url(message.content) for message in messages)
        )


class NoScamBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(commands.when_mentioned, intents=intents)
        self.store = MessageStore()

    async def delete_message(
        self, message: Message | discord.Message | discord.PartialMessage
    ) -> None:
        if isinstance(message, Message):
            channel = bot.get_channel(message.channel_id) or await bot.fetch_channel(
                message.channel_id
            )
            if isinstance(
                channel,
                discord.ForumChannel
                | discord.CategoryChannel
                | discord.abc.PrivateChannel,
            ):
                return

            message = channel.get_partial_message(message.id)

        with contextlib.suppress(discord.NotFound, discord.Forbidden):
            logger.info(f"Deleting message {message.id} in {message.guild!r}")
            await message.delete()


bot = NoScamBot()


@bot.event
async def on_message(message: discord.Message) -> None:
    # Skip bot messages, DMs, and webhooks
    if message.author.bot or message.guild is None or message.webhook_id is not None:
        return

    store = bot.store
    store.add_message(message)

    if store.is_scam(message):
        # Delete the scam messages
        scam_messages = store.get_scam_messages(message)
        for scam_message in scam_messages:
            await bot.delete_message(scam_message)

        # Timeout the user
        if isinstance(message.author, discord.Member):
            try:
                logger.info(f"Timing out {message.author!r}")
                await message.author.timeout(
                    datetime.timedelta(minutes=TIMEOUT_MINUTES),
                    reason="Sending scam messages",
                )
            except (discord.NotFound, discord.Forbidden):
                logger.info(f"Failed to time out {message.author!r}")
                pass
            else:
                logger.info(f"Timed out {message.author!r}")
                await message.channel.send(
                    f"Timed out {message.author.mention} for {TIMEOUT_MINUTES} minutes for sending scam messages"
                )

        store.clear_messages(message.guild.id, message.author.id)


load_dotenv()
bot.run(os.environ["TOKEN"])
