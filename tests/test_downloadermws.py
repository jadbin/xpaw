# coding=utf-8

import pytest
from aiohttp import web
import asyncio
import aiohttp

from xpaw.config import Config
from xpaw.http import HttpRequest, HttpResponse
from xpaw.downloadermws import *
from xpaw.errors import IgnoreRequest, ResponseNotMatch


class Cluster:
    def __init__(self, loop=None, **kwargs):
        self.loop = loop
        self.config = Config(kwargs)


class TestForwardedForMiddleware:
    async def test_handle_request(self):
        mw = ForwardedForMiddleware()
        req = HttpRequest("http://httpbin.org")
        await mw.handle_request(req)
        assert re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", req.headers["X-Forwarded-For"])


class TestDefaultHeadersMiddleware:
    async def test_handle_request(self):
        default_headers = {"User-Agent": "xpaw", "Connection": "keep-alive"}
        req_headers = {"User-Agent": "xpaw-test", "Connection": "keep-alive"}
        mw = DefaultHeadersMiddleware.from_cluster(Cluster(default_headers=default_headers))
        req = HttpRequest("http://httpbin.org", headers={"User-Agent": "xpaw-test"})
        await mw.handle_request(req)
        assert req_headers == req.headers


def make_proxy_list():
    return ["127.0.0.1:3128", "127.0.0.2:3128"]


def make_another_proxy_list():
    return ["127.0.0.1:8080", "127.0.0.2:8080"]


def make_detail_proxy_list():
    return [{'addr': '127.0.0.1:3128'},
            {'addr': '127.0.0.2:3128', 'scheme': 'http'},
            {'addr': '127.0.0.3:3128', 'scheme': 'https', 'auth': 'root:123456'}]


async def make_proxy_agent(test_server):
    def get_proxies(request):
        return web.Response(body=json.dumps(server.proxy_list).encode("utf-8"),
                            charset="utf-8",
                            content_type="application/json")

    app = web.Application()
    app.router.add_route("GET", "/", get_proxies)
    server = await test_server(app)
    server.proxy_list = make_proxy_list()
    return server


class Random:
    def __init__(self):
        self.iter = 0

    def randint(self, a, b):
        res = a + self.iter % (b - a + 1)
        self.iter += 1
        return res


class TestProxyMiddleware:
    async def test_handle_request(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', Random().randint)
        proxy_list = make_proxy_list()
        mw = ProxyMiddleware.from_cluster(Cluster(request_proxy=proxy_list))
        target_list = proxy_list * 2
        req = HttpRequest("http://httpbin.org")
        for i in range(len(target_list)):
            await mw.handle_request(req)
            assert req.proxy == target_list[i]

    async def test_handle_request2(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', Random().randint)
        proxy_list = make_detail_proxy_list()
        mw = ProxyMiddleware.from_cluster(Cluster(request_proxy=proxy_list))
        reqs = [HttpRequest('http://httpbin.org'),
                HttpRequest('https://httpbin.org'),
                HttpRequest('https://httpbin.org'),
                HttpRequest('http://httpbin.org')]
        target_list = ['127.0.0.1:3128', '127.0.0.3:3128', '127.0.0.1:3128', '127.0.0.2:3128']
        for i in range(len(reqs)):
            await mw.handle_request(reqs[i])
            assert reqs[i].proxy == target_list[i]


class TestProxyAgentMiddleware:
    async def test_handle_request(self, monkeypatch, test_server, loop):
        monkeypatch.setattr(random, 'randint', Random().randint)
        server = await make_proxy_agent(test_server)
        mw = ProxyAgentMiddleware.from_cluster(
            Cluster(proxy_agent={"agent_addr": "http://{}:{}".format(server.host, server.port)},
                    loop=loop))
        mw.open()
        req = HttpRequest("http://httpbin.org")
        target_list = make_proxy_list() * 2
        for i in range(len(target_list)):
            await mw.handle_request(req)
            assert req.proxy == target_list[i]
        mw.close()

    async def test_handle_request2(self, monkeypatch, test_server, loop):
        monkeypatch.setattr(random, 'randint', Random().randint)
        server = await make_proxy_agent(test_server)
        server.proxy_list = make_detail_proxy_list()
        mw = ProxyAgentMiddleware.from_cluster(
            Cluster(proxy_agent={"agent_addr": "http://{}:{}".format(server.host, server.port)},
                    loop=loop))
        mw.open()
        reqs = [HttpRequest('http://httpbin.org'),
                HttpRequest('https://httpbin.org'),
                HttpRequest('https://httpbin.org'),
                HttpRequest('http://httpbin.org')]
        target_list = ['127.0.0.1:3128', '127.0.0.3:3128', '127.0.0.1:3128', '127.0.0.2:3128']
        for i in range(len(reqs)):
            await mw.handle_request(reqs[i])
            assert reqs[i].proxy == target_list[i]
        mw.close()

    async def test_update_proxy_list(self, monkeypatch, test_server, loop):
        monkeypatch.setattr(random, 'randint', Random().randint)
        server = await make_proxy_agent(test_server)
        mw = ProxyAgentMiddleware.from_cluster(
            Cluster(proxy_agent={"agent_addr": "http://{}:{}".format(server.host, server.port),
                                 "update_interval": 0.05},
                    loop=loop))
        mw.open()
        await asyncio.sleep(0.1, loop=loop)
        req = HttpRequest("http://httpbin.org")
        target_list = make_proxy_list() * 2
        for i in range(len(target_list)):
            await mw.handle_request(req)
            assert req.proxy == target_list[i]
        server.proxy_list = make_another_proxy_list()
        await asyncio.sleep(0.1, loop=loop)
        target_list = make_another_proxy_list() * 2
        for i in range(len(target_list)):
            await mw.handle_request(req)
            assert req.proxy == target_list[i]
        mw.close()


class TestRetryMiddleware:
    async def test_handle_reponse(self, monkeypatch, loop):
        class ErrorFlag(Exception):
            pass

        def _retry(request, reason):
            assert isinstance(request, HttpRequest) and isinstance(reason, str)
            raise ErrorFlag

        mw = RetryMiddleware.from_cluster(Cluster(loop=loop))
        monkeypatch.setattr(mw, "retry", _retry)
        req = HttpRequest("http://httpbin.org")
        resp = HttpResponse(URL("http://httpbin.org"), 400)
        await mw.handle_response(req, resp)
        with pytest.raises(ErrorFlag):
            resp = HttpResponse(URL("http://httpbin.org"), 503)
            await mw.handle_response(req, resp)

    async def test_handle_error(self, loop, monkeypatch):
        class ErrorFlag(Exception):
            pass

        def _retry(request, reason):
            assert isinstance(request, HttpRequest) and isinstance(reason, str)
            raise ErrorFlag

        mw = RetryMiddleware.from_cluster(Cluster(loop=loop))
        monkeypatch.setattr(mw, "retry", _retry)
        req = HttpRequest("http://httpbin.org")
        err = ValueError()
        await mw.handle_error(req, err)
        with pytest.raises(ErrorFlag):
            err = ResponseNotMatch()
            await mw.handle_error(req, err)

    async def test_retry(self, loop):
        max_retry_times = 2
        mw = RetryMiddleware.from_cluster(Cluster(retry={"max_retry_times": max_retry_times},
                                                  loop=loop))
        req = HttpRequest("http://httpbin.org")
        for i in range(max_retry_times):
            req = mw.retry(req, "")
            assert isinstance(req, HttpRequest)
        with pytest.raises(IgnoreRequest):
            mw.retry(req, "")

    def test_match_status(self):
        assert RetryMiddleware.match_status("200", 200) is True
        assert RetryMiddleware.match_status(200, 200) is True
        assert RetryMiddleware.match_status("2xX", 201) is True
        assert RetryMiddleware.match_status("40x", 403) is True
        assert RetryMiddleware.match_status("40X", 403) is True
        assert RetryMiddleware.match_status("50x", 403) is False
        assert RetryMiddleware.match_status("~20X", 200) is False
        assert RetryMiddleware.match_status("!20x", 400) is True
        assert RetryMiddleware.match_status("0200", 200) is False


class TestResponseMatchMiddleware:
    async def test_handle_response(self, loop):
        req_baidu = HttpRequest("http://www.baidu.com")
        req_qq = HttpRequest("http://www.qq.com")
        resp_baidu = HttpResponse(URL("http://www.baidu.com"), 200, body="<title>百度一下，你就知道</title>".encode("utf-8"))
        resp_qq = HttpResponse(URL("http://www.qq.com"), 200, body="<title>腾讯QQ</title>".encode("utf-8"))
        mw = ResponseMatchMiddleware.from_cluster(Cluster(response_match=[{"url_pattern": "baidu\\.com",
                                                                           "body_pattern": "百度",
                                                                           "encoding": "utf-8"}],
                                                          loop=loop))
        await mw.handle_response(req_baidu, resp_baidu)
        with pytest.raises(ResponseNotMatch):
            await mw.handle_response(req_baidu, resp_qq)
        await mw.handle_response(req_qq, resp_qq)


class TestSpeedLimitMiddleware:
    def test_value_error(self):
        with pytest.raises(ValueError):
            SpeedLimitMiddleware(0, 1)
        with pytest.raises(ValueError):
            SpeedLimitMiddleware(1, 0)
        with pytest.raises(ValueError):
            SpeedLimitMiddleware(1, 1.1)

    async def test_handle_request(self, loop):
        class Counter:
            def __init__(self):
                self.n = 0

            def inc(self):
                self.n += 1

        async def processor():
            while True:
                await mw.handle_request(None)
                counter.inc()

        counter = Counter()
        mw = SpeedLimitMiddleware.from_cluster(Cluster(speed_limit={'rate': 1000, 'burst': 5},
                                                       loop=loop))
        futures = []
        for i in range(100):
            futures.append(asyncio.ensure_future(processor(), loop=loop))
        mw.open()
        await asyncio.sleep(0.1, loop=loop)
        mw.close()
        for f in futures:
            assert f.cancel() is True
        await asyncio.sleep(0.01, loop=loop)
        assert counter.n <= 105
