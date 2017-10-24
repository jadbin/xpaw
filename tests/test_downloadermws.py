# coding=utf-8

import re
import json
import random
import asyncio

import pytest
from aiohttp import web
from yarl import URL

from xpaw.config import Config
from xpaw.http import HttpRequest, HttpResponse
from xpaw.downloadermws import *
from xpaw.errors import IgnoreRequest, ResponseNotMatch


class TestForwardedForMiddleware:
    async def test_handle_request(self):
        mw = ForwardedForMiddleware()
        req = HttpRequest("http://httpbin.org")
        await mw.handle_request(req)
        assert re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", req.headers["X-Forwarded-For"])


class TestRequestHeadersMiddleware:
    async def test_handle_request(self):
        headers = {"Content-Type": "text/html", "User-Agent": "xpaw", "Connection": "keep-alive"}
        mw = RequestHeadersMiddleware.from_config(dict(request_headers=headers))
        req = HttpRequest("http://httpbin.org")
        await mw.handle_request(req)
        assert headers == req.headers


def make_proxy_list():
    return ["127.0.0.1:3128", "127.0.0.1:8080"]


def make_another_proxy_list():
    return ["127.0.0.1:8888", "127.0.0.2:9090"]


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
    async def test_hanle_request(self, monkeypatch):
        monkeypatch.setattr(random, 'randint', Random().randint)
        proxy_list = make_proxy_list()
        mw = ProxyMiddleware(proxy_list)
        target_list = proxy_list * 2
        req = HttpRequest("http://httpbin.org")
        for i in range(len(target_list)):
            await mw.handle_request(req)
            assert req.proxy == "http://{}".format(target_list[i])


class TestProxyAgentMiddleware:
    async def test_handle_request(self, monkeypatch, test_server, loop):
        monkeypatch.setattr(random, 'randint', Random().randint)
        server = await make_proxy_agent(test_server)
        mw = ProxyAgentMiddleware.from_config(
            Config({"proxy_agent":
                        {"agent_addr": "http://{}:{}".format(server.host, server.port)},
                    "downloader_loop": loop}))
        mw.open()
        req = HttpRequest("http://httpbin.org")
        target_list = make_proxy_list() * 2
        for i in range(len(target_list)):
            await mw.handle_request(req)
            assert req.proxy == "http://{}".format(target_list[i])
        mw.close()

    async def test_update_proxy_list(self, test_server, loop):
        server = await make_proxy_agent(test_server)
        mw = ProxyAgentMiddleware.from_config(
            Config({"proxy_agent": {"agent_addr": "http://{}:{}".format(server.host, server.port),
                                    "update_interval": 0.05},
                    "downloader_loop": loop}))
        mw.open()
        await asyncio.sleep(0.1, loop=loop)
        assert mw._proxy_list == make_proxy_list()
        server.proxy_list = make_another_proxy_list()
        await asyncio.sleep(0.1, loop=loop)
        assert mw._proxy_list == make_another_proxy_list()
        mw.close()


class TestRetryMiddleware:
    async def test_handle_reponse(self, monkeypatch, loop):
        class ErrorFlag(Exception):
            pass

        def _retry(request, reason):
            assert isinstance(request, HttpRequest) and isinstance(reason, str)
            raise ErrorFlag

        mw = RetryMiddleware.from_config(Config({"downloader_loop": loop}))
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

        mw = RetryMiddleware.from_config(Config({"downloader_loop": loop}))
        monkeypatch.setattr(mw, "retry", _retry)
        req = HttpRequest("http://httpbin.org")
        err = ValueError()
        await mw.handle_error(req, err)
        with pytest.raises(ErrorFlag):
            err = ResponseNotMatch()
            await mw.handle_error(req, err)

    async def test_retry(self, loop):
        max_retry_times = 2
        mw = RetryMiddleware.from_config(Config({"retry": {"max_retry_times": max_retry_times},
                                                 "downloader_loop": loop}))
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
        mw = ResponseMatchMiddleware.from_config(Config({"response_match": [{"url_pattern": "baidu\\.com",
                                                                             "body_pattern": "百度",
                                                                             "encoding": "utf-8"}],
                                                         "downloader_loop": loop}))
        await mw.handle_response(req_baidu, resp_baidu)
        with pytest.raises(ResponseNotMatch):
            await mw.handle_response(req_baidu, resp_qq)
        await mw.handle_response(req_qq, resp_qq)


class TestCookieJarMiddleware:
    async def test_handle_request(self, loop):
        mw = CookieJarMiddleware.from_config(Config({"downloader_loop": loop}))
        req = HttpRequest("http://httpbin.org")
        await mw.handle_request(req)
        assert req.meta.get("cookie_jar") is mw._cookie_jar
