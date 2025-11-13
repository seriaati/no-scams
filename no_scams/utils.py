from __future__ import annotations

import io
import logging
import re
from typing import Any

import discord
import imagehash
from PIL import Image

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


def get_image_hash(fp: io.BytesIO) -> imagehash.ImageHash:
    return imagehash.average_hash(Image.open(fp))


def contains_url(content: str) -> bool:
    return re.search(r"https?://\S+", content) is not None


def all_same(lst: list[Any]) -> bool:
    if not lst or len(lst) == 1:
        return False
    if not lst[0]:
        return False
    return all(x == lst[0] for x in lst)


def all_different(lst: list[Any]) -> bool:
    if not lst or len(lst) == 1:
        return True
    return len(set(lst)) == len(lst)


async def extract_image_hash(
    image_hashes: list[imagehash.ImageHash], attachment: discord.Attachment
) -> None:
    buffer = io.BytesIO()
    image_data = await attachment.read()
    buffer.write(image_data)
    buffer.seek(0)
    image_hashes.append(get_image_hash(buffer))
