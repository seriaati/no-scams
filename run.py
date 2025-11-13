from __future__ import annotations

import contextlib
import datetime
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Self

import discord
import imagehash
from discord.ext import commands
from dotenv import load_dotenv

from no_scams.utils import all_different, all_same, contains_url, extract_image_hash

MAX_MESSAGE_NUM = 3
TIMEOUT_MINUTES = 15
SPECIAL_GUILD_CHANNELS = {875392637299990628: 973232047193751582}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

logger = logging.getLogger("discord.bot")

intents = discord.Intents.default()
intents.message_content = True
permissions = discord.Permissions(
    moderate_members=True, manage_messages=True, read_message_history=True, send_messages=True
)
allowed_mentions = discord.AllowedMentions(everyone=False, roles=False, users=True)


@dataclass(kw_only=True)
class Message:
    id: int
    channel_id: int
    content: str
    image_hashes: frozenset[imagehash.ImageHash]

    @classmethod
    async def from_discord_message(cls, message: discord.Message) -> Self:
        image_hashes = []

        for attachment in message.attachments:
            if attachment.content_type is None:
                continue
            if not attachment.content_type.startswith("image/"):
                continue

            filename = attachment.filename.lower()
            if not any(filename.endswith(ext) for ext in IMAGE_EXTENSIONS):
                continue

            await extract_image_hash(image_hashes, attachment)

        return cls(
            id=message.id,
            channel_id=message.channel.id,
            content=message.content,
            image_hashes=frozenset(image_hashes),
        )


class MessageStore:
    def __init__(self) -> None:
        self._messages: defaultdict[tuple[int, int], list[Message]] = defaultdict(list)
        """(guild ID, author ID) -> list of messages"""

    async def add_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return

        self._messages[message.guild.id, message.author.id].append(
            await Message.from_discord_message(message)
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

        same_content = all_same([msg.content for msg in messages])
        different_channels = all_different([msg.channel_id for msg in messages])
        all_contain_url = all(contains_url(msg.content) for msg in messages)
        same_images = all_same([msg.image_hashes for msg in messages])

        if os.getenv("DEBUG"):
            logger.info(
                "%s, %s, %s, %s", same_content, different_channels, all_contain_url, same_images
            )

        return different_channels and ((all_contain_url and same_content) or (same_images))


class NoScamBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(commands.when_mentioned, intents=intents)
        self.store = MessageStore()
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

        with contextlib.suppress(discord.NotFound, discord.Forbidden):
            logger.info("Deleting message %s in %r", message.id, message.guild)
            await message.delete()

    async def on_ready(self) -> None:
        logger.info("Invite: %s", discord.utils.oauth_url(self.user.id, permissions=permissions))


bot = NoScamBot()


@bot.event
async def on_message(message: discord.Message) -> None:
    # Skip bot messages, DMs, and webhooks
    if message.author.bot or message.guild is None or message.webhook_id is not None:
        return

    store = bot.store
    await store.add_message(message)

    if store.is_scam(message):
        # Delete the scam messages
        scam_messages = store.get_scam_messages(message)
        for scam_message in scam_messages:
            await bot.delete_message(scam_message)

        # Timeout the user
        if isinstance(message.author, discord.Member):
            try:
                logger.info("Timing out %r", message.author)
                await message.author.timeout(
                    datetime.timedelta(minutes=TIMEOUT_MINUTES), reason="Sending scam messages"
                )
            except (discord.NotFound, discord.Forbidden):
                logger.info("Failed to timeout %r", message.author)
            else:
                logger.info("Timed out %r", message.author)
                timeout_msg = f"Timed out {message.author.mention} for {TIMEOUT_MINUTES} minutes for sending scam messages"

                if channel_id := SPECIAL_GUILD_CHANNELS.get(message.guild.id):
                    special_channel = message.guild.get_channel(
                        channel_id
                    ) or await message.guild.fetch_channel(channel_id)
                    if isinstance(
                        special_channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)
                    ):
                        await special_channel.send(timeout_msg)
                else:
                    await message.channel.send(timeout_msg)

        store.clear_messages(message.guild.id, message.author.id)


load_dotenv()
bot.run(os.environ["TOKEN"])
