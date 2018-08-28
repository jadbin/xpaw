# coding=utf-8

import json
import random

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


async def make_auth_server(aiohttp_server, login=None, password=None):
    async def process(request):
        auth_str = request.headers.get('Authorization')
        if auth_str is None:
            if login is not None:
                return web.Response(status=401)
        else:
            auth = BasicAuth.decode(auth_str)
            if login != auth.login or password != auth.password:
                return web.Response(status=401)
        return web.Response(status=200)

    app = web.Application()
    app.router.add_route("GET", "/{tail:.*}", process)
    server = await aiohttp_server(app)
    return server


async def test_basic_auth(aiohttp_server, loop):
    downloader = Downloader(loop=loop)
    server = await make_auth_server(aiohttp_server, login='login', password='pass')

    async def no_auth():
        req = HttpRequest("http://{}:{}/basic-auth/login/pass".format(server.host, server.port))
        resp = await downloader.download(req)
        assert resp.status == 401

    async def str_auth():
        req = HttpRequest("http://{}:{}/basic-auth/login/pass".format(server.host, server.port))
        req.meta['auth'] = 'login:pass'
        resp = await downloader.download(req)
        assert resp.status == 200

    async def tuple_auth():
        req = HttpRequest("http://{}:{}/basic-auth/login/pass".format(server.host, server.port))
        req.meta['auth'] = ('login', 'pass')
        resp = await downloader.download(req)
        assert resp.status == 200

    async def basic_auth():
        req = HttpRequest("http://{}:{}/basic-auth/login/pass".format(server.host, server.port))
        req.meta['auth'] = BasicAuth('login', 'pass')
        resp = await downloader.download(req)
        assert resp.status == 200

    async def url_basic_auth():
        resp = await downloader.download(
            HttpRequest("http://login:pass@{}:{}/basic-auth/login/pass".format(server.host, server.port)))
        assert resp.status == 200

    await no_auth()
    await str_auth()
    await tuple_auth()
    await basic_auth()
    await url_basic_auth()


async def make_params_server(aiohttp_server):
    async def process(request):
        d = {}
        for i in set(request.rel_url.query.keys()):
            v = request.rel_url.query.getall(i)
            if len(v) == 1:
                d[i] = v[0]
            else:
                d[i] = v
        return web.json_response(d, status=200)

    app = web.Application()
    app.router.add_route("GET", "/{tail:.*}", process)
    server = await aiohttp_server(app)
    return server


async def test_params(aiohttp_server, loop):
    server = await make_params_server(aiohttp_server)
    downloader = Downloader(loop=loop)
    args = {'key': 'value', 'none': '', 'list': ['item1', 'item2']}

    async def query_params():
        url = "http://{}:{}/?key=value&none=&list=item1&list=item2".format(server.host, server.port)
        resp = await downloader.download(HttpRequest(url))
        assert args == json.loads(resp.text)

    async def dict_params():
        resp = await downloader.download(HttpRequest("http://{}:{}/".format(server.host, server.port),
                                                     params={'key': 'value', 'none': '', 'list': ['item1', 'item2']}))
        assert args == json.loads(resp.text)

    async def multi_dict_params():
        params = MultiDict()
        params.add('key', 'value')
        params.add('none', '')
        params.add('list', 'item1')
        params.add('list', 'item2')
        resp = await downloader.download(HttpRequest("http://{}:{}/".format(server.host, server.port),
                                                     params=params))
        assert args == json.loads(resp.text)

    await query_params()
    await dict_params()
    await multi_dict_params()


async def make_proxy_auth_server(aiohttp_server, login=None, password=None):
    async def process(request):
        auth_str = request.headers.get('Proxy-Authorization')
        if auth_str is None:
            if login is not None:
                return web.Response(status=401)
        else:
            auth = BasicAuth.decode(auth_str)
            if login != auth.login or password != auth.password:
                return web.Response(status=401)
        return web.Response(body=request.raw_path, status=200)

    app = web.Application()
    app.router.add_route("GET", "/{tail:.*}", process)
    server = await aiohttp_server(app)
    return server


async def test_proxy(aiohttp_server, loop):
    server = await make_proxy_auth_server(aiohttp_server)
    downloader = Downloader(loop=loop)
    seed = str(random.randint(0, 2147483647))
    req = HttpRequest('http://example.com/?seed={}'.format(seed))
    req.meta['proxy'] = '{}:{}'.format(server.host, server.port)
    resp = await downloader.download(req)
    assert resp.text == req.url


async def test_proxy_auth(aiohttp_server, loop):
    downloader = Downloader(loop=loop)
    server = await make_proxy_auth_server(aiohttp_server, login='login', password='pass')

    async def no_auth():
        req = HttpRequest("http://example.com/basic-auth/login/pass")
        req.meta['proxy'] = 'http://{}:{}'.format(server.host, server.port)
        resp = await downloader.download(req)
        assert resp.status == 401

    async def str_auth():
        req = HttpRequest("http://example.com/basic-auth/login/pass")
        req.meta['proxy'] = 'http://{}:{}'.format(server.host, server.port)
        req.meta['proxy_auth'] = 'login:pass'
        resp = await downloader.download(req)
        assert resp.status == 200

    async def tuple_auth():
        req = HttpRequest("http://example.com/basic-auth/login/pass")
        req.meta['proxy'] = 'http://{}:{}'.format(server.host, server.port)
        req.meta['proxy_auth'] = ('login', 'pass')
        resp = await downloader.download(req)
        assert resp.status == 200

    async def basic_auth():
        req = HttpRequest("http://example.com/basic-auth/login/pass")
        req.meta['proxy'] = 'http://{}:{}'.format(server.host, server.port)
        req.meta['proxy_auth'] = BasicAuth('login', 'pass')
        resp = await downloader.download(req)
        assert resp.status == 200

    async def url_basic_auth():
        req = HttpRequest("http://example.com/basic-auth/login/pass")
        req.meta['proxy'] = 'http://login:pass@{}:{}'.format(server.host, server.port)
        resp = await downloader.download(req)
        assert resp.status == 200

    await no_auth()
    await str_auth()
    await tuple_auth()
    await basic_auth()
    await url_basic_auth()


async def make_headers_server(aiohttp_server):
    async def process(request):
        return web.json_response({'headers': dict(request.headers)})

    app = web.Application()
    app.router.add_route("GET", "/{tail:.*}", process)
    server = await aiohttp_server(app)
    return server


async def test_headers(aiohttp_server, loop):
    server = await make_headers_server(aiohttp_server)
    downloader = Downloader(loop=loop)
    headers = {'User-Agent': 'xpaw', 'X-My-Header': 'my-header'}
    resp = await downloader.download(HttpRequest("http://{}:{}".format(server.host, server.port),
                                                 headers=headers))
    assert resp.status == 200
    data = json.loads(resp.body.decode('utf-8'))['headers']
    assert 'User-Agent' in data and data['User-Agent'] == 'xpaw'
    assert 'X-My-Header' in data and data['X-My-Header'] == 'my-header'


async def make_post_server(aiohttp_server):
    async def process(request):
        data = await request.read()
        return web.Response(body=data, status=200)

    async def process_json(request):
        data = await request.json()
        return web.json_response(data, status=200)

    async def process_form(request):
        data = await request.post()
        d = {}
        for i in set(data.keys()):
            v = data.getall(i)
            if len(v) == 1:
                d[i] = v[0]
            else:
                d[i] = v
        return web.json_response(d, status=200)

    app = web.Application()
    app.router.add_route("POST", "/", process)
    app.router.add_route("POST", "/json", process_json)
    app.router.add_route("POST", "/form", process_form)
    server = await aiohttp_server(app)
    return server


async def test_body(aiohttp_server, loop):
    server = await make_post_server(aiohttp_server)
    downloader = Downloader(loop=loop)

    async def post_json():
        json_data = {'key': 'value', 'none': None, 'list': ['item1', 'item2'], 'object': {'name': 'object'}}
        resp = await downloader.download(HttpRequest('http://{}:{}/json'.format(server.host, server.port),
                                                     'POST', body=json_data))
        assert resp.status == 200
        data = json.loads(resp.body.decode())
        assert data == json_data

    async def post_form():
        form_data = {'key': 'value', 'none': '', 'list': ['item1', 'item2']}
        resp = await downloader.download(HttpRequest('http://{}:{}/form'.format(server.host, server.port),
                                                     'POST', body=FormData(form_data)))
        assert resp.status == 200
        data = json.loads(resp.body.decode())
        assert data == form_data

    async def post_str():
        str_data = 'str data: 字符串数据'
        resp = await downloader.download(HttpRequest('http://{}:{}/'.format(server.host, server.port),
                                                     'POST', body=str_data))
        assert resp.status == 200
        body = resp.body.decode()
        assert body == str_data

    async def post_bytes():
        bytes_data = 'bytes data: 字节数据'
        resp = await downloader.download(HttpRequest('http://{}:{}/'.format(server.host, server.port),
                                                     'POST', body=bytes_data.encode()))
        assert resp.status == 200
        body = resp.body.decode()
        assert body == bytes_data

    await post_json()
    await post_form()
    await post_str()
    await post_bytes()


async def make_redirect_server(aiohttp_server):
    async def process(request):
        return web.Response(headers={'Location': 'http://python.org/'}, status=302)

    app = web.Application()
    app.router.add_route("GET", "/{tail:.*}", process)
    server = await aiohttp_server(app)
    return server


async def test_allow_redirects(aiohttp_server, loop):
    server = await make_redirect_server(aiohttp_server)
    downloader = Downloader(loop=loop, allow_redirects=True)
    downloader2 = Downloader(loop=loop, allow_redirects=False)

    resp = await downloader.download(HttpRequest('http://{}:{}/'.format(server.host, server.port)))
    assert resp.status // 100 == 2 and 'python.org' in str(resp.url)

    resp = await downloader2.download(HttpRequest('http://{}:{}/'.format(server.host, server.port)))
    assert resp.status // 100 == 3

    req = HttpRequest('http://{}:{}/'.format(server.host, server.port))
    req.meta['allow_redirects'] = False
    resp = await downloader.download(req)
    assert resp.status // 100 == 3

    req = HttpRequest('http://{}:{}/'.format(server.host, server.port))
    req.meta['allow_redirects'] = True
    resp = await downloader2.download(req)
    assert resp.status // 100 == 2 and 'python.org' in str(resp.url)


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
    cluster = Cluster(downloader_middlewares=[lambda d=data: FooDownloadermw(d),
                                              DummyDownloadermw,
                                              FooAsyncDownloaderMw],
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
    cluster2 = Cluster(downloader_middlewares={lambda d=data2: FooDownloadermw(d): 0},
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
