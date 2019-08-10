# coding=utf-8

import logging
import asyncio

from xpaw.errors import NotEnabled

log = logging.getLogger(__name__)

__all__ = ['SpeedLimitMiddleware']


class SpeedLimitMiddleware:
    def __init__(self, rate=1, burst=1):
        self._rate = rate
        self._burst = burst
        if self._rate <= 0:
            raise ValueError("rate must be greater than 0")
        if self._burst <= 0:
            raise ValueError('burst must be greater than 0')
        self._interval = 1.0 / self._rate
        self._bucket = self._burst
        self._semaphore = asyncio.Semaphore(self._burst)
        self._update_future = None

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(speed_limit_rate={}, speed_limit_burst={})'.format(cls_name, repr(self._rate), repr(self._burst))

    @classmethod
    def from_crawler(cls, crawler):
        config = crawler.config
        if config['speed_limit'] is None:
            raise NotEnabled
        return cls(**config['speed_limit'])

    async def handle_request(self, request):
        await self._semaphore.acquire()
        self._bucket -= 1

    async def _update_value(self):
        while True:
            await asyncio.sleep(self._interval)
            if self._bucket + 1 <= self._burst:
                self._bucket += 1
                self._semaphore.release()

    def open(self):
        self._update_future = asyncio.ensure_future(self._update_value())

    def close(self):
        if self._update_future:
            self._update_future.cancel()
