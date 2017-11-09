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
from xpaw.spidermws import DepthMiddleware
from xpaw import defaultconfig


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
        if len(self.data) >= self.tot:
            asyncio.ensure_future(self.cluster.shutdown(), loop=self.cluster.loop)


class MyError(Exception):
    pass


class LinkDownloaderMiddleware:
    def handle_request(self, request):
        if request.url == 'http://httpbin.org/status/406':
            return HttpRequest('http://httpbin.org/status/407', dont_filter=True)
        if request.url == 'http://httpbin.org/status/410':
            raise MyError

    def handle_response(self, request, response):
        if request.url == 'http://httpbin.org/status/407':
            return HttpRequest('http://httpbin.org/status/409')

    def handle_error(self, request, error):
        if isinstance(error, MyError):
            return HttpRequest('http://httpbin.org/status/411')


class LinkSpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.link_count = self.config.get('link_count')

    @every(seconds=30)
    def start_requests(self):
        yield HttpRequest("http://localhost", errback=self.error_back)
        yield HttpRequest("http://localhost", errback=self.async_error_back, dont_filter=True)
        yield HttpRequest("http://httpbin.org/status/401", callback=self.generator_parse)
        yield HttpRequest("http://httpbin.org/status/402", callback=self.func_prase)
        yield HttpRequest("http://httpbin.org/status/403", callback=self.async_parse)
        yield HttpRequest("http://httpbin.org/status/404", callback=self.return_list_parse)
        yield HttpRequest("http://httpbin.org/status/405", callback=self.return_none)
        yield HttpRequest("http://httpbin.org/status/406", dont_filter=True)
        yield HttpRequest("http://httpbin.org/status/408")
        yield HttpRequest("http://httpbin.org/status/410", dont_filter=True)
        yield HttpRequest("http://httpbin.org/links/{}".format(self.link_count), dont_filter=True)

    def parse(self, response):
        selector = Selector(response.text)
        for href in selector.xpath('//a/@href').text:
            yield HttpRequest(urljoin(str(response.url), href))
        yield LinkItem(url=response.request.url)

    def error_back(self, request, err):
        raise RuntimeError('not an error actually')

    async def async_error_back(self, request, err):
        raise RuntimeError('not an error actually')

    def generator_parse(self, response):
        if response.status / 100 != 2:
            raise RuntimeError('not an error actually')
        yield None

    def func_prase(self, response):
        raise RuntimeError('not an error actually')

    async def async_parse(self, response):
        raise RuntimeError('not an error actually')

    def return_list_parse(self, response):
        return []

    def return_none(self, response):
        pass


def test_run_link_spider():
    link_data = set()
    link_count = 5
    link_total = 7
    run_spider(LinkSpider, downloader_timeout=60, log_level='DEBUG', item_pipelines=[LinkPipeline],
               link_data=link_data, link_count=link_count, link_total=link_total, max_retry_times=1,
               downloader_clients=1, spider_middlewares=[DepthMiddleware],
               downloader_middlewares=[LinkDownloaderMiddleware])
    assert len(link_data) == link_total
    for i in range(link_count):
        assert "http://httpbin.org/links/{}/{}".format(link_count, i) in link_data
    assert "http://httpbin.org/status/409" in link_data
    assert "http://httpbin.org/status/411" in link_data
    logging.getLogger('xpaw').handlers.clear()
