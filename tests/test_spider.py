# coding=utf-8

import pytest

from xpaw.spider import Spider
from xpaw import events

from .crawler import Crawler


class FooSpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = self.config['data']

    def open(self):
        super().open()
        self.data['open'] = ''

    def close(self):
        super().close()
        self.data['close'] = ''


@pytest.mark.asyncio
async def test_spider():
    data = {}
    crawler = Crawler(data=data)
    spider = FooSpider.from_crawler(crawler)
    await crawler.event_bus.send(events.crawler_start)
    with pytest.raises(NotImplementedError):
        spider.start_requests()
    with pytest.raises(NotImplementedError):
        spider.parse(None)
    await crawler.event_bus.send(events.crawler_shutdown)
    assert 'open' in data and 'close' in data
