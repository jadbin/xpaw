# coding=utf-8

import pytest

from xpaw.spider import SpiderMiddlewareManager, Spider
from xpaw import events
from .crawler import Crawler


class FooSpidermw:
    def __init__(self, d):
        self.d = d

    def open(self):
        self.d['open'] = ''

    def close(self):
        self.d['close'] = ''

    def handle_start_requests(self, result):
        res = []
        for r in result:
            self.d['handle_start_requests'] = r
            res.append(r)
        return res

    def handle_input(self, response):
        self.d['handle_input'] = response

    def handle_output(self, response, result):
        res = []
        for r in result:
            self.d['handle_output'] = (response, r)
            res.append(r)
        return res

    def handle_error(self, response, error):
        self.d['handle_error'] = (response, error)


class DummySpidermw:
    """
    no method
    """


class FooAsyncSpiderMw(FooSpidermw):
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.config['data'])

    @pytest.mark.asyncio
    async def handle_start_requests(self, result):
        res = []
        for r in result:
            self.d['async_handle_start_requests'] = r
            res.append(r)
        return res

    @pytest.mark.asyncio
    async def handle_input(self, response):
        self.d['async_handle_input'] = response

    @pytest.mark.asyncio
    async def handle_output(self, response, result):
        res = []
        for r in result:
            self.d['async_handle_output'] = (response, r)
            res.append(r)
        return res

    @pytest.mark.asyncio
    async def handle_error(self, response, error):
        self.d['async_handle_error'] = (response, error)


@pytest.mark.asyncio
async def test_spider_middleware_manager_handlers():
    data = {}
    crawler = Crawler(spider_middlewares=[lambda d=data: FooSpidermw(d),
                                          DummySpidermw,
                                          FooAsyncSpiderMw],
                      default_spider_middlewares=None,
                      data=data)
    spidermw = SpiderMiddlewareManager.from_crawler(crawler)
    response_obj = object()
    result_obj = object()
    error_obj = object()
    await crawler.event_bus.send(events.crawler_start)
    await spidermw._handle_start_requests((result_obj,))
    await spidermw._handle_input(response_obj)
    await spidermw._handle_output(response_obj, (result_obj,))
    await spidermw._handle_error(response_obj, error_obj)
    await crawler.event_bus.send(events.crawler_shutdown)
    assert 'open' in data and 'close' in data
    assert data['handle_start_requests'] is result_obj
    assert data['handle_input'] is response_obj
    assert data['handle_output'][0] is response_obj and data['handle_output'][1] is result_obj
    assert data['handle_error'][0] is response_obj and data['handle_error'][1] is error_obj
    assert data['async_handle_start_requests'] is result_obj
    assert data['async_handle_input'] is response_obj
    assert data['async_handle_output'][0] is response_obj and data['async_handle_output'][1] is result_obj
    assert data['async_handle_error'][0] is response_obj and data['async_handle_error'][1] is error_obj

    data2 = {}
    crawler2 = Crawler(spider_middlewares={lambda d=data2: FooSpidermw(d): 0},
                       default_spider_middlewares=None,
                       data=data2)
    spidermw2 = SpiderMiddlewareManager.from_crawler(crawler2)
    response_obj2 = object()
    await crawler2.event_bus.send(events.crawler_start)
    await spidermw2._handle_input(response_obj2)
    await crawler2.event_bus.send(events.crawler_shutdown)
    assert 'open' in data2 and 'close' in data2
    assert data2['handle_input'] is response_obj2

    crawler3 = Crawler(spider_middlewares=None, default_spider_middlewares=None, data={})
    SpiderMiddlewareManager.from_crawler(crawler3)


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
