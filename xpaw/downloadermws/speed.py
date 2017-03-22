# coding=utf-8

import logging
import asyncio

from xpaw.config import BaseConfig

log = logging.getLogger(__name__)


class SpeedLimitMiddleware:
    def __init__(self, span, burst, loop=None):
        if span <= 0:
            raise ValueError("span must greater than 0")
        self._span = span
        self._burst = burst
        self._loop = loop or asyncio.get_event_loop()
        self._semaphore = asyncio.Semaphore(0, loop=loop)
        self._value = 0
        self._update_future = None

    @classmethod
    def from_config(cls, config):
        c = config.get("speed_limit")
        if c is None:
            c = {}
        c = BaseConfig(c)
        return cls(c.getfloat("span", 1),
                   c.getint("burst", 1),
                   loop=config.get("downloader_loop"))

    async def handle_request(self, request):
        await self._semaphore.acquire()
        self._value -= 1

    async def _update_value(self):
        while True:
            log.debug("Update speed limit semaphore")
            d = self._burst - self._value
            if d > 0:
                self._value += d
                i = 0
                while i < d:
                    self._semaphore.release()
                    i += 1
            await asyncio.sleep(self._span)

    def open(self):
        self._update_future = asyncio.ensure_future(self._update_value(), loop=self._loop)

    def close(self):
        if self._update_future:
            self._update_future.cancel()
