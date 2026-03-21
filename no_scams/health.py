import logging
from typing import Self

import discord
from aiohttp import web

logger = logging.getLogger("discord.bot.health")


class HealthCheckServer:
    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.app = web.Application()
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.stop()

    async def health(self, _request: web.Request) -> web.Response:
        if self.bot.is_ready() and not self.bot.is_closed():
            return web.Response(text="OK", status=200)
        return web.Response(text="Not Ready", status=503)

    async def start(self, *, port: int = 8080) -> None:
        self.app.add_routes([web.get("/health", self.health)])
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", port)
        await self.site.start()

        logger.info("Health check server started on port %s", port)

    async def stop(self) -> None:
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

        logger.info("Health check server stopped")
