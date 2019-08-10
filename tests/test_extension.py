# coding=utf-8

import pytest

from xpaw.extension import ExtensionManager
from xpaw import events
from xpaw.http import HttpRequest, HttpResponse

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

    ExtensionManager.from_crawler(Crawler(extensions=None, default_extensions=None, data={}))


def test_make_component_list():
    cls = ExtensionManager._make_component_list
    d = cls('foo', Crawler(foo=['a', 'c'], default_foo=['b', 'd']).config)
    assert d == ['a', 'c', 'b', 'd']


class FooDownloadermw:
    def __init__(self, d):
        self.d = d

    def open(self):
        self.d['open'] = ''

    def close(self):
        self.d['close'] = ''

    def handle_request(self, request):
        self.d['handle_request'] = request

    def handle_response(self, request, response):
        self.d['handle_response'] = (request, response)

    def handle_error(self, request, error):
        self.d['handle_error'] = (request, error)


class DummyDownloadermw:
    """
    no method
    """


class FooAsyncDownloaderMw(FooDownloadermw):
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.config['data'])

    async def handle_request(self, request):
        self.d['async_handle_request'] = request

    async def handle_response(self, request, response):
        self.d['async_handle_response'] = (request, response)

    async def handle_error(self, request, error):
        self.d['async_handle_error'] = (request, error)


@pytest.mark.asyncio
async def test_downloader_middleware_manager_handlers():
    data = {}
    crawler = Crawler(extensions=[lambda d=data: FooDownloadermw(d),
                                  DummyDownloadermw,
                                  FooAsyncDownloaderMw],
                      default_extensions=None,
                      data=data)
    downloadermw = ExtensionManager.from_crawler(crawler)
    request_obj = HttpRequest(None)
    response_obj = HttpResponse(None, None)
    error_obj = object()
    await crawler.event_bus.send(events.crawler_start)
    await downloadermw.handle_request(request_obj)
    await downloadermw.handle_response(request_obj, response_obj)
    await downloadermw.handle_error(request_obj, error_obj)
    await crawler.event_bus.send(events.crawler_shutdown)
    assert 'open' in data and 'close' in data
    assert data['handle_request'] is request_obj
    assert data['handle_response'][0] is request_obj and data['handle_response'][1] is response_obj
    assert data['handle_error'][0] is request_obj and data['handle_error'][1] is error_obj
    assert data['async_handle_request'] is request_obj
    assert data['async_handle_response'][0] is request_obj and data['async_handle_response'][1] is response_obj
    assert data['async_handle_error'][0] is request_obj and data['async_handle_error'][1] is error_obj


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

    def handle_spider_input(self, response):
        self.d['handle_input'] = response

    def handle_spider_output(self, response, result):
        res = []
        for r in result:
            self.d['handle_output'] = (response, r)
            res.append(r)
        return res

    def handle_spider_error(self, response, error):
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
    async def handle_spider_input(self, response):
        self.d['async_handle_input'] = response

    @pytest.mark.asyncio
    async def handle_spider_output(self, response, result):
        res = []
        for r in result:
            self.d['async_handle_output'] = (response, r)
            res.append(r)
        return res

    @pytest.mark.asyncio
    async def handle_spider_error(self, response, error):
        self.d['async_handle_error'] = (response, error)


@pytest.mark.asyncio
async def test_spider_middleware_manager_handlers():
    data = {}
    crawler = Crawler(extensions=[lambda d=data: FooSpidermw(d),
                                  DummySpidermw,
                                  FooAsyncSpiderMw],
                      default_extensions=None,
                      data=data)
    spidermw = ExtensionManager.from_crawler(crawler)
    response_obj = object()
    result_obj = object()
    error_obj = object()
    await crawler.event_bus.send(events.crawler_start)
    await spidermw.handle_start_requests((result_obj,))
    await spidermw.handle_spider_input(response_obj)
    await spidermw.handle_spider_output(response_obj, (result_obj,))
    await spidermw.handle_spider_error(response_obj, error_obj)
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


class FooItemPipeline:
    def __init__(self, d):
        self.d = d

    def handle_item(self, item):
        self.d['handle_item'] = item

    def open(self):
        self.d['open'] = ''

    def close(self):
        self.d['close'] = ''


class DummyItemPipeline:
    """
    no method
    """


class FooAsyncItemPipeline(FooItemPipeline):
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.config['data'])

    @pytest.mark.asyncio
    async def handle_item(self, item):
        self.d['async_handle_item'] = item


@pytest.mark.asyncio
async def test_item_pipeline_manager():
    data = {}
    crawler = Crawler(extensions=[lambda d=data: FooItemPipeline(d),
                                  DummyItemPipeline,
                                  FooAsyncItemPipeline],
                      default_extensions=None,
                      data=data)
    pipeline = ExtensionManager.from_crawler(crawler)
    obj = object()
    await crawler.event_bus.send(events.crawler_start)
    await pipeline.handle_item(obj)
    await crawler.event_bus.send(events.crawler_shutdown)
    assert 'open' in data and 'close' in data
    assert data['handle_item'] is obj and data['async_handle_item'] is obj
