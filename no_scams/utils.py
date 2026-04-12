import io
import re
from typing import Any

import discord
import imagehash
from PIL import Image

from no_scams.constants import DISCORD_INVITE


def get_image_hash(fp: io.BytesIO) -> imagehash.ImageHash:
    return imagehash.average_hash(Image.open(fp))


def contains_url(content: str) -> bool:
    contains_discord_invite = re.search(DISCORD_INVITE, content) is not None
    contains_url = re.search(r"https?://\S+", content) is not None
    return contains_discord_invite or contains_url


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
