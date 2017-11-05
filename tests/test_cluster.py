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


class LinkItem(Item):
    url = Field()


class LinkPipeline:
    def __init__(self, n, data, cluster):
        self.n = n
        self.data = data
        self.cluster = cluster

    @classmethod
    def from_cluster(cls, cluster):
        n = cluster.config.getint('link_count')
        data = cluster.config.get('link_data')
        return cls(n, data, cluster)

    async def handle_item(self, item):
        url = item['url']
        if url == "http://httpbin.org/links/{}".format(self.n):
            raise IgnoreItem
        self.data.add(url)
        if len(self.data) >= self.n:
            asyncio.ensure_future(self.cluster.shutdown(), loop=self.cluster.loop)

    def open(self):
        pass

    def close(self):
        pass


class LinkSpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.link_count = self.config.get('link_count')

    @every(seconds=30)
    def start_requests(self):
        yield HttpRequest("http://httpbin.org/status/401", callback=self.generator_parse)
        yield HttpRequest("http://httpbin.org/status/402", callback=self.func_prase)
        yield HttpRequest("http://httpbin.org/status/403", callback=self.async_parse)
        yield HttpRequest("http://httpbin.org/status/404", callback=self.return_list_parse)
        yield HttpRequest("http://httpbin.org/status/405", callback=self.return_none)
        yield HttpRequest("http://httpbin.org/status/500")
        yield HttpRequest("http://localhost", errback=self.network_error)
        yield HttpRequest("http://httpbin.org/links/{}".format(self.link_count), dont_filter=True)

    def parse(self, response):
        selector = Selector(response.text)
        for href in selector.xpath('//a/@href').text:
            yield HttpRequest(urljoin(str(response.url), href))
        yield LinkItem(url=response.request.url)

    def network_error(self, request, err):
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
    link_count = 10
    run_spider(LinkSpider, downloader_timeout=60, log_level='WARNING', item_pipelines=[LinkPipeline],
               link_data=link_data, link_count=link_count, retry={'max_retry_times': 0},
               spider_middlewares=DepthMiddleware)
    assert len(link_data) == link_count
    for i in range(link_count):
        assert "http://httpbin.org/links/{}/{}".format(link_count, i) in link_data
    logging.getLogger('xpaw').handlers.clear()
