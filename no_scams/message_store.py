import datetime
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Self

import discord
import imagehash

from no_scams.constants import CONSECUTIVE_WINDOW_MINUTES, IMAGE_EXTENSIONS, MAX_MESSAGE_NUM
from no_scams.utils import all_different, all_same, contains_url, extract_image_hash

logger = logging.getLogger("discord.bot.message_store")


@dataclass(kw_only=True)
class Message:
    id: int
    channel_id: int
    content: str
    image_hashes: frozenset[imagehash.ImageHash]
    created_at: datetime.datetime

    def __str__(self) -> str:
        return f"Message(id={self.id}, channel_id={self.channel_id}, image_hashes={self.image_hashes}, created_at={self.created_at})"

    def __repr__(self) -> str:
        return self.__str__()

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
            created_at=message.created_at,
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
        all_have_images = all(msg.image_hashes for msg in messages)
        all_no_text_content = all(not msg.content.strip() for msg in messages)
        message_time_window = max(msg.created_at for msg in messages) - min(
            msg.created_at for msg in messages
        )
        within_consecutive_window = message_time_window <= datetime.timedelta(
            minutes=CONSECUTIVE_WINDOW_MINUTES
        )

        logger.debug(
            "Checking if messages are scam:\n"
            "Messages: %s\n"
            "Same content: %s\n"
            "Different channels: %s\n"
            "All contain URL: %s\n"
            "Same images: %s\n"
            "All have images: %s\n"
            "All no text content: %s\n"
            "Within consecutive window: %s",
            messages,
            same_content,
            different_channels,
            all_contain_url,
            same_images,
            all_have_images,
            all_no_text_content,
            within_consecutive_window,
        )

        return (
            different_channels
            and within_consecutive_window
            and (same_content or same_images or (all_have_images and all_no_text_content))
        )
