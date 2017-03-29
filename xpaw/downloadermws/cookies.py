# coding=utf-8

import logging
import asyncio

from aiohttp import CookieJar

log = logging.getLogger(__name__)


class CookieJarMiddleware:
    def __init__(self, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self._cookie_jar = CookieJar(loop=self._loop)

    @classmethod
    def from_config(cls, config):
        return cls(loop=config.get("downloader_loop"))

    async def handle_request(self, request):
        log.debug("Assign cookie jar to request (url={})".format(request.url))
        request.meta["cookie_jar"] = self._cookie_jar
