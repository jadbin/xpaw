# coding=utf-8

import re
import asyncio
import threading

import pytest
from aiohttp import web
from yarl import URL

from xpaw.config import Config
from xpaw.http import HttpRequest, HttpResponse
from xpaw.downloadermws import *
from xpaw.errors import IgnoreRequest, ResponseNotMatch

from .helpers import wait_server_start


@pytest.fixture(scope="module")
def loop(request):
    def close():
        loop.close()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    request.addfinalizer(close)
    return loop


class TestForwardedForMiddleware:
    def test_handle_request(self, loop):
        mw = ForwardedForMiddleware()
        req = HttpRequest("http://www.example.com")
        loop.run_until_complete(mw.handle_request(req))
        assert re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", req.headers["X-Forwarded-For"])


class TestRequestHeadersMiddleware:
    def test_handle_request(self, loop):
        headers = {"Content-Type": "text/html", "User-Agent": "xpaw", "Connection": "keep-alive"}
        mw = RequestHeadersMiddleware.from_config(dict(request_headers=headers))
        req = HttpRequest("http://www.example.com")
        loop.run_until_complete(mw.handle_request(req))
        assert headers == req.headers


@pytest.fixture(scope="module")
def agent(request):
    async def handle_request(request):
        return web.Response(body=b'["127.0.0.1:3128", "127.0.0.1:8080"]')

    def handle_error(loop, context):
        pass

    def start_loop():
        app = web.Application(loop=loop)
        app.router.add_resource("/").add_route("GET", handle_request)
        loop.run_until_complete(loop.create_server(app.make_handler(access_log=None, loop=loop), "0.0.0.0", 7340))
        try:
            loop.run_forever()
        except Exception:
            pass
        finally:
            loop.close()

    def stop_loop():
        loop.call_soon_threadsafe(loop.stop)

    loop = asyncio.new_event_loop()
    loop.set_exception_handler(handle_error)
    t = threading.Thread(target=start_loop)
    t.start()
    wait_server_start("127.0.0.1:7340")
    request.addfinalizer(stop_loop)


class TestProxyMiddleware:
    def test_hanle_request(self, loop):
        mw = ProxyMiddleware(["127.0.0.1"])
        req = HttpRequest("http://www.example.com")
        loop.run_until_complete(mw.handle_request(req))
        assert req.proxy == "http://127.0.0.1"


class TestProxyAgentMiddleware:
    def test_handle_request(self, loop, monkeypatch):
        async def _pick_proxy():
            return "http://127.0.0.1"

        mw = ProxyAgentMiddleware.from_config(Config({"proxy_agent": {"addr": "http://127.0.0.1:7340"}}))
        monkeypatch.setattr(mw, "_pick_proxy", _pick_proxy)
        req = HttpRequest("http://www.example.com")
        loop.run_until_complete(mw.handle_request(req))
        assert req.proxy == "http://127.0.0.1"

    def test_pick_proxy(self, loop, monkeypatch):
        async def _update_proxy_list():
            while self.index < 2:
                await asyncio.sleep(0.1)
                self.index += 1
                mw._proxy_list = proxy_list[self.index - 1]

        self.index = 0
        proxy_list = [[], ["127.0.0.1", "127.0.0.2"]]
        res = ["http://127.0.0.1", "http://127.0.0.2"]
        mw = ProxyAgentMiddleware.from_config(
            Config({"proxy_agent": {"addr": "127.0.0.1:7340", "update_interval": 0.1}}))
        monkeypatch.setattr(mw, "_update_proxy_list", _update_proxy_list)
        mw.open()
        for i in range(len(res)):
            req = HttpRequest("http://www.example.com")
            loop.run_until_complete(mw.handle_request(req))
            assert req.proxy in res

    def test_update_proxy_list(self, loop, agent):
        async def _func():
            while mw._proxy_list is None:
                await asyncio.sleep(0.1)

        mw = ProxyAgentMiddleware.from_config(
            Config({"proxy_agent": {"addr": "http://127.0.0.1:7340", "update_interval": 0.1}}))
        mw.open()
        loop.run_until_complete(_func())
        assert mw._proxy_list == ["127.0.0.1:3128", "127.0.0.1:8080"]
        mw.close()
        loop.run_until_complete(asyncio.sleep(0.1))


class TestRetryMiddleware:
    def test_handle_reponse(self, loop, monkeypatch):
        class ErrorFlag(Exception):
            pass

        def _retry(request, reason):
            assert isinstance(request, HttpRequest) and isinstance(reason, str)
            raise ErrorFlag

        mw = RetryMiddleware.from_config(Config())
        monkeypatch.setattr(mw, "retry", _retry)
        req = HttpRequest("http://www.example.com")
        resp = HttpResponse(URL("http://www.example.com"), 400)
        loop.run_until_complete(mw.handle_response(req, resp))
        with pytest.raises(ErrorFlag):
            resp = HttpResponse(URL("http://www.example.com"), 503)
            loop.run_until_complete(mw.handle_response(req, resp))

    def test_handle_error(self, loop, monkeypatch):
        class ErrorFlag(Exception):
            pass

        def _retry(request, reason):
            assert isinstance(request, HttpRequest) and isinstance(reason, str)
            raise ErrorFlag

        mw = RetryMiddleware.from_config(Config())
        monkeypatch.setattr(mw, "retry", _retry)
        req = HttpRequest("http://www.example.com")
        err = ValueError()
        loop.run_until_complete(mw.handle_error(req, err))
        with pytest.raises(ErrorFlag):
            err = ResponseNotMatch()
            loop.run_until_complete(mw.handle_error(req, err))

    def test_retry(self):
        max_retry_times = 2
        mw = RetryMiddleware.from_config(Config({"retry": {"max_retry_times": max_retry_times}}))
        req = HttpRequest("http://www.example.com")
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


class TestResponseMatchMiddleware:
    def test_handle_response(self, loop):
        req_baidu = HttpRequest("http://www.baidu.com")
        req_qq = HttpRequest("http://www.qq.com")
        resp_baidu = HttpResponse(URL("http://www.baidu.com"), 200, body="<title>百度一下，你就知道</title>".encode("utf-8"))
        resp_qq = HttpResponse(URL("http://www.qq.com"), 200, body="<title>腾讯QQ</title>".encode("utf-8"))
        mw = ResponseMatchMiddleware.from_config(Config({"response_match": [{"url_pattern": "baidu\\.com",
                                                                             "body_pattern": "百度",
                                                                             "encoding": "utf-8"}]}))
        loop.run_until_complete(mw.handle_response(req_baidu, resp_baidu))
        with pytest.raises(ResponseNotMatch):
            loop.run_until_complete(mw.handle_response(req_baidu, resp_qq))
        loop.run_until_complete(mw.handle_response(req_qq, resp_qq))


class TestCookieJarMiddleware:
    def test_handle_request(self, loop):
        mw = CookieJarMiddleware.from_config(Config({"downloader_loop": loop}))
        req = HttpRequest("http://www.example.com")
        loop.run_until_complete(mw.handle_request(req))
        assert req.meta.get("cookie_jar") is mw._cookie_jar
