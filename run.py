from collections import defaultdict
import contextlib
from dataclasses import dataclass
import datetime
import io
import logging
import os
import re
from typing import Any, Self
from discord.ext import commands
import discord
from dotenv import load_dotenv
from PIL import Image
import imagehash

MAX_MESSAGE_NUM = 3
TIMEOUT_MINUTES = 15
SPECIAL_GUILD_CHANNELS = {875392637299990628: 973232047193751582}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

logger = logging.getLogger("discord.bot")

intents = discord.Intents.default()
intents.message_content = True
permissions = discord.Permissions(
    moderate_members=True,
    manage_messages=True,
    read_message_history=True,
    send_messages=True,
)
allowed_mentions = discord.AllowedMentions(everyone=False, roles=False, users=True)


def get_image_hash(fp: io.BytesIO) -> imagehash.ImageHash:
    return imagehash.average_hash(Image.open(fp))


def images_identical(path1, path2):
    hash1 = get_image_hash(path1)
    hash2 = get_image_hash(path2)
    return hash1 == hash2


@dataclass(kw_only=True)
class Message:
    id: int
    channel_id: int
    content: str
    image_hashes: frozenset[imagehash.ImageHash]

    @staticmethod
    async def extract_image_hash(image_hashes, attachment):
        buffer = io.BytesIO()
        image_data = await attachment.read()
        buffer.write(image_data)
        buffer.seek(0)
        image_hashes.append(get_image_hash(buffer))

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

            await cls.extract_image_hash(image_hashes, attachment)

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

    @staticmethod
    def contains_url(content: str) -> bool:
        return re.search(r"https?://\S+", content) is not None

    @staticmethod
    def all_same(lst: list[Any]) -> bool:
        if not lst or len(lst) == 1:
            return False
        if not lst[0]:
            return False
        return all(x == lst[0] for x in lst)

    @staticmethod
    def all_different(lst: list[Any]) -> bool:
        if not lst or len(lst) == 1:
            return True
        return len(set(lst)) == len(lst)

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

        same_content = self.all_same([msg.content for msg in messages])
        different_channels = self.all_different([msg.channel_id for msg in messages])
        all_contain_url = all(self.contains_url(msg.content) for msg in messages)
        same_images = self.all_same([msg.image_hashes for msg in messages])

        if os.getenv("DEBUG"):
            logger.info(
                f"{same_content=}, {different_channels=}, {all_contain_url=}, {same_images=}"
            )

        return different_channels and (
            (all_contain_url and same_content) or (same_images)
        )


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

    async def on_ready(self) -> None:
        logger.info(
            f"Invite: {discord.utils.oauth_url(self.user.id, permissions=permissions)}"
        )


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
                logger.info(f"Timing out {message.author!r}")
                await message.author.timeout(
                    datetime.timedelta(minutes=TIMEOUT_MINUTES),
                    reason="Sending scam messages",
                )
            except (discord.NotFound, discord.Forbidden):
                logger.info(f"Failed to timeout {message.author!r}")
                pass
            else:
                logger.info(f"Timed out {message.author!r}")
                timeout_msg = f"Timed out {message.author.mention} for {TIMEOUT_MINUTES} minutes for sending scam messages"

                if channel_id := SPECIAL_GUILD_CHANNELS.get(message.guild.id):
                    special_channel = message.guild.get_channel(
                        channel_id
                    ) or await message.guild.fetch_channel(channel_id)
                    if isinstance(
                        special_channel,
                        (discord.TextChannel, discord.Thread, discord.VoiceChannel),
                    ):
                        await special_channel.send(timeout_msg)
                else:
                    await message.channel.send(timeout_msg)

        store.clear_messages(message.guild.id, message.author.id)


load_dotenv()
bot.run(os.environ["TOKEN"])
