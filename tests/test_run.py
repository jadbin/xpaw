# coding=utf-8

from os.path import join, exists
import asyncio
from urllib.parse import urljoin
import os
import signal
import sys
import time

import pytest

from xpaw.cli import main
from xpaw.run import run_crawler
from xpaw.spider import Spider
from xpaw.http import HttpRequest
from xpaw.selector import Selector
from xpaw.run import run_spider
from xpaw.item import Item, Field
from xpaw.errors import IgnoreItem
from xpaw.queue import PriorityQueue


def test_run_crawler(tmpdir, capsys):
    proj_name = 'test_run_crawler'
    proj_dir = join(str(tmpdir), proj_name)
    main(argv=['xpaw', 'init', proj_dir])
    run_crawler(proj_dir, downloader_timeout=0.01, log_level='WARNING')
    _, _ = capsys.readouterr()


class FooSpider(Spider):
    def start_requests(self):
        yield HttpRequest('http://httpbin.org/get')

    async def parse(self, response):
        pass


class BadQueue(PriorityQueue):
    async def pop(self):
        await super().pop()
        await asyncio.sleep(0.2)
        raise RuntimeError('not an error actually')


class BadQueue2(PriorityQueue):
    async def pop(self):
        raise RuntimeError('not an error actually')


def test_coro_terminated():
    run_spider(FooSpider, downloader_clients=2, queue=BadQueue, max_retry_times=0, downloader_timeout=0.1)


def test_coro_terminated2():
    run_spider(FooSpider, downloader_clients=2, queue=BadQueue2, max_retry_times=0, downloader_timeout=0.1)


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


def test_link_spider():
    link_data = set()
    link_count = 5
    link_total = 15
    run_spider(LinkSpider, downloader_timeout=60, log_level='DEBUG', item_pipelines=[LinkPipeline],
               link_data=link_data, link_count=link_count, max_retry_times=1,
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


class WaitSpider(Spider):
    def start_requests(self):
        yield HttpRequest('http://httpbin.org/get')

    async def parse(self, response):
        while True:
            await asyncio.sleep(5)


def check_pid(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def test_wait_spider(tmpdir, monkeypatch):
    monkeypatch.setattr(os, '_exit', sys.exit)
    pid_file = join(str(tmpdir), 'pid')
    log_file = join(str(tmpdir), 'log')
    with pytest.raises(SystemExit) as excinfo:
        run_spider(WaitSpider, pid_file=pid_file, log_file=log_file, daemon=True)
    assert excinfo.value.code == 0
    t = 10
    while t > 0 and not exists(pid_file):
        t -= 1
        time.sleep(1)
    assert t > 0
    with open(pid_file, 'rb') as f:
        pid = int(f.read().decode())
    assert check_pid(pid) is True
    os.kill(pid, signal.SIGTERM)
    t = 10
    while t > 0 and exists(pid_file):
        t -= 1
        time.sleep(1)
    assert t > 0
