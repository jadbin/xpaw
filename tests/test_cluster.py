# coding=utf-8

from os.path import join, exists
import asyncio
import os
import signal
import time
from threading import Thread

from xpaw.spider import Spider
from xpaw.http import HttpRequest
from xpaw.queue import PriorityQueue
from xpaw.run import run_spider
from xpaw.item import Item
from xpaw.errors import IgnoreItem


class SleepSpider(Spider):
    async def start_requests(self):
        await asyncio.sleep(0.2, loop=self.cluster.loop)

    def parse(self, response):
        pass


def test_supervisor():
    run_spider(SleepSpider, downloader_timeout=0.1)


class StartRequestSpider(Spider):
    def start_requests(self):
        yield HttpRequest('http://python.org/')

    async def parse(self, response):
        pass


class BadQueue(PriorityQueue):
    def __init__(self, loop=None, **kwargs):
        super().__init__(loop=loop, **kwargs)
        self.loop = loop

    async def pop(self):
        await super().pop()
        raise RuntimeError('not an error actually')


class BadQueue2(PriorityQueue):
    async def pop(self):
        raise RuntimeError('not an error actually')


def test_coro_terminated():
    run_spider(StartRequestSpider, downloader_clients=2, queue=BadQueue, max_retry_times=0, downloader_timeout=0.1)


def test_coro_terminated2():
    run_spider(StartRequestSpider, downloader_clients=2, queue=BadQueue2, max_retry_times=0, downloader_timeout=0.1)


class ToKillSpider(Spider):
    def start_requests(self):
        yield HttpRequest('http://python.org/')

    async def parse(self, response):
        while True:
            await asyncio.sleep(5, loop=self.cluster.loop)


class ExceptionThread(Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bucket = []

    def run(self):
        try:
            super().run()
        except Exception as e:
            self.bucket.append(e)
            raise


def test_kill_spider(tmpdir):
    pid_file = join(str(tmpdir), 'pid')
    log_file = join(str(tmpdir), 'log')
    t = ExceptionThread(target=kill_spider, args=(pid_file,))
    t.start()
    run_spider(ToKillSpider, pid_file=pid_file, log_file=log_file)
    t.join()
    assert len(t.bucket) == 0, 'Exception in thread'


def _check_pid(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def kill_spider(pid_file):
    t = 10
    while t > 0 and not exists(pid_file):
        t -= 1
        time.sleep(1)
    assert t > 0
    with open(pid_file, 'rb') as f:
        pid = int(f.read().decode())
    assert _check_pid(pid) is True
    os.kill(pid, signal.SIGTERM)
    t = 10
    while t > 0 and exists(pid_file):
        t -= 1
        time.sleep(1)
    assert t > 0


class FooError(Exception):
    pass


class HandlerDownloaderMiddleware:
    def handle_request(self, request):
        if request.url.endswith('error'):
            raise FooError


class HandlerSpiderMiddleware:
    def handle_input(self, response):
        if response.request.url.endswith('not-found'):
            raise FooError

    def handle_error(self, response, error):
        if isinstance(error, FooError):
            return ()


class HandlerSpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = self.config.get('data')
        self.server_address = self.config.get('server_address')

    def start_requests(self):
        yield HttpRequest("http://localhost:80", errback=self.error_back)
        yield HttpRequest("http://localhost:80", dont_filter=True, errback=self.async_error_back)
        yield HttpRequest("http://{}/error".format(self.server_address), errback=self.handle_request_error)
        yield HttpRequest("http://{}/not-found".format(self.server_address), errback=self.handle_input_error)
        yield HttpRequest("http://{}/".format(self.server_address), dont_filter=True)
        yield HttpRequest("http://{}/".format(self.server_address), dont_filter=True, callback=self.generator_parse)
        yield HttpRequest("http://{}/".format(self.server_address), dont_filter=True, callback=self.func_prase)
        yield HttpRequest("http://{}/".format(self.server_address), dont_filter=True, callback=self.async_parse)
        yield HttpRequest("http://{}/".format(self.server_address), dont_filter=True, callback=self.return_list_parse)
        yield HttpRequest("http://{}/".format(self.server_address), dont_filter=True, callback=self.return_none_parse)

    def parse(self, response):
        self.data.add('parse')

    def error_back(self, request, err):
        self.data.add('error_back')
        raise RuntimeError('not an error actually')

    async def async_error_back(self, request, err):
        self.data.add('async_error_back')
        raise RuntimeError('not an error actually')

    def handle_request_error(self, request, error):
        assert isinstance(error, FooError)
        self.data.add('handle_request_error')

    def handle_input_error(self, request, error):
        assert isinstance(error, FooError)
        self.data.add('handle_input_error')

    def generator_parse(self, response):
        self.data.add('generator_parse')
        if response.status / 100 != 2:
            raise RuntimeError('not an error actually')
        # it will never come here
        yield None

    def func_prase(self, response):
        self.data.add('func_parse')
        raise RuntimeError('not an error actually')

    async def async_parse(self, response):
        self.data.add('async_parse')
        raise RuntimeError('not an error actually')

    def return_list_parse(self, response):
        self.data.add('return_list_parse')
        return []

    def return_none_parse(self, response):
        self.data.add('return_none_parse')


def test_spider_handlers():
    data = set()
    run_spider(HandlerSpider, log_level='DEBUG', spider_middlewares=[HandlerSpiderMiddleware],
               downloader_middlewares=[HandlerDownloaderMiddleware], data=data,
               server_address='python.org')
    assert 'parse' in data
    assert 'error_back' in data
    assert 'async_error_back' in data
    assert 'handle_request_error' in data
    assert 'handle_input_error' in data
    assert 'generator_parse' in data
    assert 'func_parse' in data
    assert 'async_parse' in data
    assert 'return_list_parse' in data
    assert 'return_none_parse' in data


class DummyItem(Item):
    pass


class DroppedItem(Item):
    pass


class ErrorItem(Item):
    pass


class FooItemPipeLine:
    def __init__(self, data):
        self.data = data

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config.get('data'))

    def handle_item(self, item):
        if isinstance(item, DroppedItem):
            raise IgnoreItem
        elif isinstance(item, ErrorItem):
            raise RuntimeError('not an error actually')
        self.data['item'] = item


class ItemSpider(Spider):
    def start_requests(self):
        yield HttpRequest('http://python.org/')

    def parse(self, response):
        yield DroppedItem()
        yield ErrorItem()
        yield DummyItem()


def test_handle_item():
    data = {}
    run_spider(ItemSpider, log_level='DEBUG', data=data, item_pipelines=[FooItemPipeLine])
    assert isinstance(data.get('item'), DummyItem)


class ToDumpSpider(Spider):
    def start_requests(self):
        yield HttpRequest('http://python.org/', callback=self.parse_response, meta={'key': 'value'})

    async def parse_response(self, response):
        while True:
            await asyncio.sleep(5, loop=self.cluster.loop)


class ToLoadSpider(Spider):
    def start_requests(self):
        pass

    async def parse_response(self, response):
        data = self.config.get('data')
        data['url'] = response.request.url
        data['meta'] = response.meta


def test_dump_request(tmpdir):
    dump_dir = str(tmpdir)
    pid_file = join(dump_dir, 'pid')
    t = Thread(target=kill_spider, args=(pid_file,))
    t.start()
    run_spider(ToDumpSpider, dump_dir=dump_dir, pid_file=pid_file, cookie_jar_enabled=True)
    t.join()
    data = {}
    run_spider(ToLoadSpider, dump_dir=dump_dir, data=data, cookie_jar_enabled=True)
    assert data['url'] == 'http://python.org/'
    assert data['meta']['key'] == 'value'
