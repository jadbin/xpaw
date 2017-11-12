# coding=utf-8

import asyncio
import logging
from urllib.parse import urljoin

from xpaw.spider import Spider
from xpaw.http import HttpRequest
from xpaw.selector import Selector
from xpaw.run import run_spider
from xpaw.handler import every
from xpaw.item import Item, Field
from xpaw.errors import IgnoreItem
from xpaw.queue import PriorityQueue


class FooSpider(Spider):
    def start_requests(self):
        yield HttpRequest('http://localhost:80')
        yield HttpRequest('http://httpbin.org/get')

    async def parse(self, response):
        await asyncio.sleep(1, loop=self.cluster.loop)
        return ()


class BadQueue(PriorityQueue):
    async def pop(self):
        req = await super().pop()
        if req.url == 'http://localhost:80':
            raise RuntimeError('not an error actually')
        return req


def test_coro_terminated():
    run_spider(FooSpider, downloader_timeout=1, downloader_clients=2, queue_cls=BadQueue, max_retry_times=0)
    logging.getLogger('xpaw').handlers.clear()


class LinkItem(Item):
    url = Field()


class LinkPipeline:
    def __init__(self, n, tot, data, cluster):
        self.n = n
        self.tot = tot
        self.data = data
        self.cluster = cluster

    @classmethod
    def from_cluster(cls, cluster):
        n = cluster.config.getint('link_count')
        data = cluster.config.get('link_data')
        tot = cluster.config.getint('link_total')
        return cls(n, tot, data, cluster)

    async def handle_item(self, item):
        url = item['url']
        if url == "http://httpbin.org/links/{}".format(self.n):
            raise IgnoreItem
        self.data.add(url)


class MyError(Exception):
    pass


class LinkDownloaderMiddleware:
    def handle_request(self, request):
        if request.url == 'http://httpbin.org/status/406':
            return HttpRequest('http://httpbin.org/status/407')
        if request.url == 'http://httpbin.org/status/410':
            raise MyError

    def handle_response(self, request, response):
        if request.url == 'http://httpbin.org/status/407':
            return HttpRequest('http://httpbin.org/status/409')

    def handle_error(self, request, error):
        if isinstance(error, MyError):
            return HttpRequest('http://httpbin.org/status/411')


class LinkSpiderMiddleware:
    def handle_input(self, response):
        if response.request.url == 'http://httpbin.org/status/412':
            raise MyError

    def handle_output(self, response, result):
        return result

    def handle_error(self, response, error):
        if isinstance(error, MyError):
            return ()


class LinkSpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.link_count = self.config.get('link_count')
        self.data = self.config.get('link_data')
        self.tot = self.config.get('link_total')

    def open(self):
        asyncio.ensure_future(self.supervisor(), loop=self.cluster.loop)

    async def supervisor(self):
        while True:
            if len(self.data) >= self.tot:
                asyncio.ensure_future(self.cluster.shutdown(), loop=self.cluster.loop)
                break
            await asyncio.sleep(1, loop=self.cluster.loop)

    @every(seconds=30)
    def start_requests(self):
        yield HttpRequest("http://localhost:80", errback=self.error_back)
        yield HttpRequest("http://localhost:81", errback=self.async_error_back)
        yield HttpRequest("http://httpbin.org/status/401", callback=self.generator_parse)
        yield HttpRequest("http://httpbin.org/status/402", callback=self.func_prase)
        yield HttpRequest("http://httpbin.org/status/403", callback=self.async_parse)
        yield HttpRequest("http://httpbin.org/status/404", callback=self.return_list_parse)
        yield HttpRequest("http://httpbin.org/status/405", callback=self.return_none)
        yield HttpRequest("http://httpbin.org/status/406")
        yield HttpRequest("http://httpbin.org/status/408")
        yield HttpRequest("http://httpbin.org/status/410")
        yield HttpRequest("http://httpbin.org/status/412", errback=self.handle_input_error)
        yield HttpRequest("http://httpbin.org/links/{}".format(self.link_count))

    def parse(self, response):
        selector = Selector(response.text)
        for href in selector.xpath('//a/@href').text:
            yield HttpRequest(urljoin(str(response.url), href))
        yield LinkItem(url=response.request.url)

    def error_back(self, request, err):
        self.data.add(request.url)
        raise RuntimeError('not an error actually')

    async def async_error_back(self, request, err):
        self.data.add(request.url)
        raise RuntimeError('not an error actually')

    def generator_parse(self, response):
        self.data.add(response.request.url)
        if response.status / 100 != 2:
            raise RuntimeError('not an error actually')
        # it will never come here
        yield None

    def func_prase(self, response):
        self.data.add(response.request.url)
        raise RuntimeError('not an error actually')

    async def async_parse(self, response):
        self.data.add(response.request.url)
        raise RuntimeError('not an error actually')

    def return_list_parse(self, response):
        self.data.add(response.request.url)
        return []

    def return_none(self, response):
        self.data.add(response.request.url)

    def handle_input_error(self, request, error):
        assert isinstance(error, MyError)
        self.data.add(request.url)


def test_run_link_spider():
    link_data = set()
    link_count = 5
    link_total = 15
    run_spider(LinkSpider, downloader_timeout=60, log_level='DEBUG', item_pipelines=[LinkPipeline],
               link_data=link_data, link_count=link_count, link_total=link_total, max_retry_times=1,
               downloader_clients=10, spider_middlewares=[LinkSpiderMiddleware],
               downloader_middlewares=[LinkDownloaderMiddleware])
    assert len(link_data) == link_total
    for i in range(link_count):
        assert "http://httpbin.org/links/{}/{}".format(link_count, i) in link_data
    assert "http://localhost:80" in link_data
    assert "http://localhost:81" in link_data
    assert "http://httpbin.org/status/401" in link_data
    assert "http://httpbin.org/status/402" in link_data
    assert "http://httpbin.org/status/403" in link_data
    assert "http://httpbin.org/status/404" in link_data
    assert "http://httpbin.org/status/405" in link_data
    assert "http://httpbin.org/status/409" in link_data
    assert "http://httpbin.org/status/411" in link_data
    assert "http://httpbin.org/status/412" in link_data
    logging.getLogger('xpaw').handlers.clear()
