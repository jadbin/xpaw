# coding=utf-8

import pytest

from xpaw.spider import SpiderMiddlewareManager, Spider
from xpaw.eventbus import EventBus
from xpaw.config import Config
from xpaw import events


class MySpidermw:
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


class MyEmptySpidermw:
    """
    no method
    """


class MyAsyncSpiderMw(MySpidermw):
    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config['data'])

    async def handle_start_requests(self, result):
        res = []
        for r in result:
            self.d['async_handle_start_requests'] = r
            res.append(r)
        return res

    async def handle_input(self, response):
        self.d['async_handle_input'] = response

    async def handle_output(self, response, result):
        res = []
        for r in result:
            self.d['async_handle_output'] = (response, r)
            res.append(r)
        return res

    async def handle_error(self, response, error):
        self.d['async_handle_error'] = (response, error)


class Cluster:
    def __init__(self, **kwargs):
        self.event_bus = EventBus()
        self.config = Config(kwargs)


async def test_spider_middleware_manager_handlers():
    data = {}
    cluster = Cluster(spider_middlewares=[lambda d=data: MySpidermw(d),
                                          MyEmptySpidermw,
                                          MyAsyncSpiderMw],
                      spider_middlewares_base=None,
                      data=data)
    spidermw = SpiderMiddlewareManager.from_cluster(cluster)
    response_obj = object()
    result_obj = object()
    error_obj = object()
    await cluster.event_bus.send(events.cluster_start)
    await spidermw._handle_start_requests((result_obj,))
    await spidermw._handle_input(response_obj)
    await spidermw._handle_output(response_obj, (result_obj,))
    await spidermw._handle_error(response_obj, error_obj)
    await cluster.event_bus.send(events.cluster_shutdown)
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
    cluster2 = Cluster(spider_middlewares={lambda d=data2: MySpidermw(d): 0},
                       spider_middlewares_base=None,
                       data=data2)
    spidermw2 = SpiderMiddlewareManager.from_cluster(cluster2)
    response_obj2 = object()
    await cluster2.event_bus.send(events.cluster_start)
    await spidermw2._handle_input(response_obj2)
    await cluster2.event_bus.send(events.cluster_shutdown)
    assert 'open' in data2 and 'close' in data2
    assert data2['handle_input'] is response_obj2

    cluster3 = Cluster(spider_middlewares=None, spider_middlewares_base=None, data={})
    SpiderMiddlewareManager.from_cluster(cluster3)


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


async def test_spider(loop):
    data = {}
    cluster = Cluster(data=data, loop=loop)
    spider = FooSpider.from_cluster(cluster)
    await cluster.event_bus.send(events.cluster_start)
    with pytest.raises(NotImplementedError):
        spider.start_requests()
    with pytest.raises(NotImplementedError):
        spider.parse(None)
    await cluster.event_bus.send(events.cluster_shutdown)
    assert 'open' in data and 'close' in data
