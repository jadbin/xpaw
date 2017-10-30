# coding=utf-8

import asyncio
from urllib.parse import urljoin

from xpaw.spider import Spider
from xpaw.http import HttpRequest
from xpaw.selector import Selector
from xpaw.run import run_spider
from xpaw import events


class LinkSpider(Spider):
    n = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.urls = []
        self.cluster.event_bus.subscribe(self.response_received, events.response_received)

    def start_requests(self):
        yield HttpRequest("http://httpbin.org/links/{}".format(self.n))

    def parse(self, response):
        selector = Selector(response.text)
        for href in selector.xpath('//a/@href').text:
            yield HttpRequest(urljoin(str(response.url), href))

    def response_received(self, response):
        self.urls.append(response.request.url)
        if len(self.urls) > self.n:
            assert "http://httpbin.org/links/{}".format(self.n) in self.urls
            for i in range(self.n):
                assert "http://httpbin.org/links/{}/{}".format(self.n, i) in self.urls
            asyncio.ensure_future(self.cluster.shutdown(), loop=self.cluster.loop)


def test_run_link_spider():
    run_spider(LinkSpider, downloader_timeout=60, log_level='WARNING')
