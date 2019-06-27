# coding=utf-8

import json

import pytest

from xpaw.http import HttpRequest, HttpResponse
from xpaw.downloader import Downloader, DownloaderMiddlewareManager
from xpaw import events
from xpaw.errors import HttpError
from xpaw.utils import make_url

from .crawler import Crawler


@pytest.mark.asyncio
async def test_basic_auth():
    downloader = Downloader()

    async def no_auth():
        req = HttpRequest("http://httpbin.org/basic-auth/user/passwd")
        with pytest.raises(HttpError) as e:
            await downloader.fetch(req)
        assert e.value.response.status == 401

    async def tuple_auth():
        req = HttpRequest("http://httpbin.org/basic-auth/user/passwd")
        req.auth = ('user', 'passwd')
        resp = await downloader.fetch(req)
        assert resp.status == 200

    await no_auth()
    await tuple_auth()


@pytest.mark.asyncio
async def test_params():
    downloader = Downloader()

    async def query_params():
        url = "http://httpbin.org/anything?key=value&none="
        resp = await downloader.fetch(HttpRequest(url))
        assert json.loads(resp.text)['args'] == {'key': 'value', 'none': ''}

    async def dict_params():
        resp = await downloader.fetch(
            HttpRequest(make_url("http://httpbin.org/get", params={'key': 'value', 'none': ''})))
        assert json.loads(resp.text)['args'] == {'key': 'value', 'none': ''}

    async def list_params():
        resp = await downloader.fetch(HttpRequest(make_url("http://httpbin.org/get",
                                                           params=[('list', '1'), ('list', '2')])))
        assert json.loads(resp.text)['args'] == {'list': ['1', '2']}

    await query_params()
    await dict_params()
    await list_params()


@pytest.mark.asyncio
async def test_headers():
    downloader = Downloader()
    headers = {'User-Agent': 'xpaw'}
    resp = await downloader.fetch(HttpRequest("http://httpbin.org/get",
                                              headers=headers))
    assert resp.status == 200
    data = json.loads(resp.text)['headers']
    assert 'User-Agent' in data and data['User-Agent'] == 'xpaw'


@pytest.mark.asyncio
async def test_body():
    downloader = Downloader()

    async def post_str():
        str_data = 'str data: 字符串数据'
        resp = await downloader.fetch(HttpRequest('http://httpbin.org/post',
                                                  'POST', body=str_data,
                                                  headers={'Content-Type': 'text/plain'}))
        assert resp.status == 200
        body = json.loads(resp.text)['data']
        assert body == str_data

    async def post_bytes():
        bytes_data = 'bytes data: 字节数据'
        resp = await downloader.fetch(HttpRequest('http://httpbin.org/post',
                                                  'POST', body=bytes_data.encode(),
                                                  headers={'Content-Type': 'text/plain'}))
        assert resp.status == 200
        body = json.loads(resp.text)['data']
        assert body == bytes_data

    await post_str()
    await post_bytes()


@pytest.mark.asyncio
async def test_allow_redirects():
    downloader = Downloader()

    resp = await downloader.fetch(HttpRequest(make_url('http://httpbin.org/redirect-to',
                                                       params={'url': 'http://python.org'})))
    assert resp.status // 100 == 2 and 'python.org' in resp.url

    with pytest.raises(HttpError) as e:
        await downloader.fetch(HttpRequest(make_url('http://httpbin.org/redirect-to',
                                                    params={'url': 'http://python.org'}),
                                           allow_redirects=False))
    assert e.value.response.status // 100 == 3


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
    crawler = Crawler(downloader_middlewares=[lambda d=data: FooDownloadermw(d),
                                              DummyDownloadermw,
                                              FooAsyncDownloaderMw],
                      default_downloader_middlewares=None,
                      data=data)
    downloadermw = DownloaderMiddlewareManager.from_crawler(crawler)
    request_obj = HttpRequest(None)
    response_obj = HttpResponse(None, None)
    error_obj = object()
    await crawler.event_bus.send(events.crawler_start)
    await downloadermw._handle_request(request_obj)
    await downloadermw._handle_response(request_obj, response_obj)
    await downloadermw._handle_error(request_obj, error_obj)
    await crawler.event_bus.send(events.crawler_shutdown)
    assert 'open' in data and 'close' in data
    assert data['handle_request'] is request_obj
    assert data['handle_response'][0] is request_obj and data['handle_response'][1] is response_obj
    assert data['handle_error'][0] is request_obj and data['handle_error'][1] is error_obj
    assert data['async_handle_request'] is request_obj
    assert data['async_handle_response'][0] is request_obj and data['async_handle_response'][1] is response_obj
    assert data['async_handle_error'][0] is request_obj and data['async_handle_error'][1] is error_obj

    data2 = {}
    crawler2 = Crawler(downloader_middlewares={lambda d=data2: FooDownloadermw(d): 0},
                       default_downloader_middlewares=None,
                       data=data2)
    downloadermw2 = DownloaderMiddlewareManager.from_crawler(crawler2)
    request_obj2 = HttpRequest(None)
    await crawler2.event_bus.send(events.crawler_start)
    await downloadermw2._handle_request(request_obj2)
    await crawler2.event_bus.send(events.crawler_shutdown)
    assert 'open' in data2 and 'close' in data2
    assert data2['handle_request'] is request_obj2

    crawler3 = Crawler(downloader_middlewares=None, default_downloader_middlewares=None, data={})
    DownloaderMiddlewareManager.from_crawler(crawler3)
