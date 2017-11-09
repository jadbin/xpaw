# coding=utf-8

import json
import random
import asyncio
import base64

import aiohttp
from aiohttp import web
from aiohttp.helpers import BasicAuth
from multidict import MultiDict
from aiohttp import FormData

from xpaw.http import HttpRequest
from xpaw.downloader import Downloader, DownloaderMiddlewareManager
from xpaw.eventbus import EventBus
from xpaw.config import Config
from xpaw import events


async def test_cookies(loop):
    downloader = Downloader(timeout=60, loop=loop)
    seed = str(random.randint(0, 2147483647))
    req = HttpRequest("http://httpbin.org/cookies", cookies={"seed": seed})
    resp = await downloader.download(req)
    assert resp.status == 200
    cookies = json.loads(resp.text)["cookies"]
    assert len(cookies) == 1 and cookies.get("seed") == seed


async def test_cookie_jar(loop):
    downloader = Downloader(timeout=60, cookie_jar_enabled=True, loop=loop)
    seed = str(random.randint(0, 2147483647))
    await downloader.download(HttpRequest("http://httpbin.org/cookies/set?seed={}".format(seed)))
    resp = await downloader.download(HttpRequest("http://httpbin.org/cookies"))
    assert resp.status == 200
    cookies = json.loads(resp.text)["cookies"]
    assert len(cookies) == 1 and cookies.get("seed") == seed
    await downloader.download(HttpRequest("http://httpbin.org/cookies/delete?seed="))
    resp = await downloader.download(HttpRequest("http://httpbin.org/cookies"))
    assert resp.status == 200
    cookies = json.loads(resp.text)["cookies"]
    assert len(cookies) == 0


async def test_basic_auth(loop):
    downloader = Downloader(timeout=60, loop=loop)

    def validate_response(resp, login):
        assert resp.status == 200
        data = json.loads(resp.body.decode())
        assert data['authenticated'] is True and data['user'] == login

    async def no_auth():
        resp = await downloader.download(HttpRequest("http://httpbin.org/basic-auth/login/password"))
        assert resp.status == 401

    async def str_auth():
        resp = await downloader.download(HttpRequest("http://httpbin.org/basic-auth/login/password",
                                                     auth='login:password'))
        validate_response(resp, 'login')

    async def tuple_auth():
        resp = await downloader.download(HttpRequest("http://httpbin.org/basic-auth/login/password",
                                                     auth=('login', 'password')))
        validate_response(resp, 'login')

    async def basic_auth():
        resp = await downloader.download(HttpRequest("http://httpbin.org/basic-auth/login/password",
                                                     auth=BasicAuth('login', 'password')))
        validate_response(resp, 'login')

    await asyncio.gather(no_auth(), str_auth(), tuple_auth(), basic_auth(), loop=loop)


async def test_params(loop):
    downloader = Downloader(timeout=60, loop=loop)

    def validate_response(resp, d):
        assert resp.status == 200
        data = json.loads(resp.body.decode())
        assert data['args'] == d

    async def query_params():
        resp = await downloader.download(HttpRequest("http://httpbin.org/get?list=2&k=v&none=&list=1"))
        validate_response(resp, {'k': 'v', 'none': '', 'list': ['2', '1']})

    async def dict_params():
        resp = await downloader.download(HttpRequest("http://httpbin.org/get",
                                                     params={'k': 'v', 'none': '', 'list': [2, 1]}))
        validate_response(resp, {'k': 'v', 'none': '', 'list': ['2', '1']})

    async def multi_dict_params():
        params = MultiDict()
        params.add('list', 2)
        params.add('k', 'v')
        params.add('none', '')
        params.add('list', 1)
        resp = await downloader.download(HttpRequest("http://httpbin.org/get",
                                                     params=params))
        validate_response(resp, {'k': 'v', 'none': '', 'list': ['2', '1']})

    async def query_and_dict_params():
        req = HttpRequest("http://httpbin.org/get?list=2&k=v")
        req.params = {'none': '', 'list': [1]}
        resp = await downloader.download(req)
        validate_response(resp, {'k': 'v', 'none': '', 'list': ['2', '1']})

    await asyncio.gather(query_params(), dict_params(), multi_dict_params(), query_and_dict_params(), loop=loop)


async def make_proxy_server(test_server, loop):
    async def process(request):
        auth_str = request.headers.get('Proxy-Authorization')
        if auth_str is None:
            auth = None
        else:
            auth = BasicAuth.decode(auth_str)
        async with aiohttp.ClientSession(loop=loop) as session:
            with aiohttp.Timeout(60, loop=loop):
                async with session.request("GET", request.raw_path, auth=auth) as resp:
                    body = await resp.read()
                    return web.Response(status=resp.status,
                                        body=body,
                                        headers=resp.headers)

    app = web.Application()
    app.router.add_route("GET", "/{tail:.*}", process)
    server = await test_server(app)
    return server


async def test_proxy(test_server, loop):
    server = await make_proxy_server(test_server, loop=loop)
    downloader = Downloader(timeout=60, loop=loop)
    seed = str(random.randint(0, 2147483647))
    resp = await downloader.download(HttpRequest('http://httpbin.org/get?seed={}'.format(seed),
                                                 proxy='{}:{}'.format(server.host, server.port)))
    args = json.loads(resp.body.decode())['args']
    assert 'seed' in args and args['seed'] == seed


async def test_proxy_auth(test_server, loop):
    downloader = Downloader(timeout=60, loop=loop)
    server = await make_proxy_server(test_server, loop=loop)

    def validate_response(resp, login):
        assert resp.status == 200
        data = json.loads(resp.body.decode())
        assert data['authenticated'] is True and data['user'] == login

    async def no_auth():
        resp = await downloader.download(HttpRequest("http://httpbin.org/basic-auth/login/password",
                                                     proxy='{}:{}'.format(server.host, server.port)))
        assert resp.status == 401

    async def str_auth():
        resp = await downloader.download(HttpRequest("http://httpbin.org/basic-auth/login/password",
                                                     proxy_auth='login:password',
                                                     proxy='{}:{}'.format(server.host, server.port)), )
        validate_response(resp, 'login')

    async def tuple_auth():
        resp = await downloader.download(HttpRequest("http://httpbin.org/basic-auth/login/password",
                                                     proxy_auth=('login', 'password'),
                                                     proxy='{}:{}'.format(server.host, server.port)))
        validate_response(resp, 'login')

    async def basic_auth():
        resp = await downloader.download(HttpRequest("http://httpbin.org/basic-auth/login/password",
                                                     proxy_auth=BasicAuth('login', 'password'),
                                                     proxy='{}:{}'.format(server.host, server.port)))
        validate_response(resp, 'login')

    await asyncio.gather(no_auth(), str_auth(), tuple_auth(), basic_auth(), loop=loop)


async def test_headers(loop):
    downloader = Downloader(timeout=60, loop=loop)
    headers = {'user-agent': 'xpaw', 'X-MY-HEADER': 'xpaw-HEADER'}
    resp = await downloader.download(HttpRequest("http://httpbin.org/get",
                                                 headers=headers))
    assert resp.status == 200
    data = json.loads(resp.body.decode())['headers']
    assert 'User-Agent' in data and data['User-Agent'] == 'xpaw'
    assert 'X-MY-HEADER' not in data
    assert 'X-My-Header' in data and data['X-My-Header'] == 'xpaw-HEADER'


async def test_post_data(loop):
    downloader = Downloader(timeout=60, loop=loop)

    async def post_json():
        json_data = {'key': 'value', 'list': [1, 2], 'obj': {'name': 'my obj'}}
        resp = await downloader.download(HttpRequest('http://httpbin.org/post', 'POST', body=json_data))
        assert resp.status == 200
        body = json.loads(resp.body.decode())
        headers = body['headers']
        assert 'Content-Type' in headers and headers['Content-Type'] == 'application/json'
        assert body['json'] == json_data

    async def post_form():
        form_data = {'key': 'value', 'list': ['1', '2']}
        resp = await downloader.download(HttpRequest('http://httpbin.org/post', 'POST', body=FormData(form_data)))
        assert resp.status == 200
        body = json.loads(resp.body.decode())
        headers = body['headers']
        assert 'Content-Type' in headers and headers['Content-Type'] == 'application/x-www-form-urlencoded'
        assert body['form'] == form_data

    async def post_str():
        str_data = 'my str data: 测试数据'
        resp = await downloader.download(HttpRequest('http://httpbin.org/post', 'POST', body=str_data))
        assert resp.status == 200
        body = json.loads(resp.body.decode())
        assert body['data'] == str_data

    async def post_bytes():
        bytes_data = 'my str data: 测试数据'.encode('gbk')
        resp = await downloader.download(HttpRequest('http://httpbin.org/post', 'POST', body=bytes_data))
        assert resp.status == 200
        body = json.loads(resp.body.decode())
        headers = body['headers']
        data = body['data']
        assert 'Content-Type' in headers and headers['Content-Type'] == 'application/octet-stream'
        assert base64.b64decode(data.split(',', 1)[1]) == bytes_data

    await asyncio.gather(post_json(), post_form(), post_str(), post_bytes(), loop=loop)


class MyDownloadermw:
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


class MyEmptyDownloadermw:
    """
    no method
    """


class MyAsyncDownloaderMw(MyDownloadermw):
    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config['data'])

    async def handle_request(self, request):
        self.d['async_handle_request'] = request

    async def handle_response(self, request, response):
        self.d['async_handle_response'] = (request, response)

    async def handle_error(self, request, error):
        self.d['async_handle_error'] = (request, error)


class Cluster:
    def __init__(self, **kwargs):
        self.event_bus = EventBus()
        self.config = Config(kwargs)


async def test_downloader_middleware_manager_handlers():
    data = {}
    cluster = Cluster(downloader_middlewares=[lambda d=data: MyDownloadermw(d),
                                              MyEmptyDownloadermw,
                                              MyAsyncDownloaderMw],
                      downloader_middlewares_base=None,
                      data=data)
    downloadermw = DownloaderMiddlewareManager.from_cluster(cluster)
    request_obj = object()
    response_obj = object()
    error_obj = object()
    await cluster.event_bus.send(events.cluster_start)
    await downloadermw._handle_request(request_obj)
    await downloadermw._handle_response(request_obj, response_obj)
    await downloadermw._handle_error(request_obj, error_obj)
    await cluster.event_bus.send(events.cluster_shutdown)
    assert 'open' in data and 'close' in data
    assert data['handle_request'] is request_obj
    assert data['handle_response'][0] is request_obj and data['handle_response'][1] is response_obj
    assert data['handle_error'][0] is request_obj and data['handle_error'][1] is error_obj
    assert data['async_handle_request'] is request_obj
    assert data['async_handle_response'][0] is request_obj and data['async_handle_response'][1] is response_obj
    assert data['async_handle_error'][0] is request_obj and data['async_handle_error'][1] is error_obj

    data2 = {}
    cluster2 = Cluster(downloader_middlewares={lambda d=data2: MyDownloadermw(d): 0},
                       downloader_middlewares_base=None,
                       data=data2)
    downloadermw2 = DownloaderMiddlewareManager.from_cluster(cluster2)
    request_obj2 = object()
    await cluster2.event_bus.send(events.cluster_start)
    await downloadermw2._handle_request(request_obj2)
    await cluster2.event_bus.send(events.cluster_shutdown)
    assert 'open' in data2 and 'close' in data2
    assert data2['handle_request'] is request_obj2

    cluster3 = Cluster(downloader_middlewares=None, downloader_middlewares_base=None, data={})
    DownloaderMiddlewareManager.from_cluster(cluster3)
