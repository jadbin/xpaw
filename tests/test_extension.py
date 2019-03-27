# coding=utf-8

import pytest

from xpaw.extension import ExtensionManager
from xpaw import events
from .crawler import Crawler


class FooExtension:
    def __init__(self, d):
        self.d = d

    def open(self):
        self.d['open'] = ''

    def close(self):
        self.d['close'] = ''


class DummyExtension:
    """
    no method
    """


@pytest.mark.asyncio
async def test_extension_manager():
    data = {}
    crawler = Crawler(extensions=[lambda d=data: FooExtension(d),
                                  DummyExtension],
                      default_extensions=None,
                      data=data)
    extensions = ExtensionManager.from_crawler(crawler)
    await crawler.event_bus.send(events.crawler_start)
    await crawler.event_bus.send(events.crawler_shutdown)
    assert 'open' in data and 'close' in data

    crawler3 = Crawler(extensions=None, default_extensions=None, data={})
    ExtensionManager.from_crawler(crawler3)
