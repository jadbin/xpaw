# coding=utf-8

import asyncio

import pytest

from xpaw.extensions import SpeedLimitMiddleware
from xpaw.errors import NotEnabled

from ..crawler import Crawler


class TestSpeedLimitMiddleware:
    @pytest.mark.asyncio
    async def test_value_error(self):
        with pytest.raises(ValueError):
            SpeedLimitMiddleware.from_crawler(Crawler(speed_limit={'rate': 0, 'burst': 1}))
        with pytest.raises(ValueError):
            SpeedLimitMiddleware.from_crawler(Crawler(speed_limit={'rate': 1, 'burst': 0}))

    @pytest.mark.asyncio
    async def test_not_enabled(self):
        with pytest.raises(NotEnabled):
            SpeedLimitMiddleware.from_crawler(Crawler())

    @pytest.mark.asyncio
    async def test_handle_request(self):
        class Counter:
            def __init__(self):
                self.n = 0

            def inc(self):
                self.n += 1

        async def processor():
            while True:
                await mw.handle_request(None)
                counter.inc()

        counter = Counter()
        mw = SpeedLimitMiddleware.from_crawler(Crawler(speed_limit={'rate': 1000, 'burst': 5}))
        futures = []
        for i in range(100):
            futures.append(asyncio.ensure_future(processor()))
        mw.open()
        await asyncio.sleep(0.1)
        mw.close()
        for f in futures:
            assert f.cancel() is True
        await asyncio.sleep(0.01)
        assert counter.n <= 105
