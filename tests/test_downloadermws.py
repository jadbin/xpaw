# coding=utf-8

import re
import time
import asyncio
import threading

import pytest
from aiohttp import web

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


@pytest.fixture(scope="class")
def agent(request):
    async def handle_request(request):
        return web.Response(body=b'["127.0.0.1:3128", "127.0.0.1:8080"]')

    def handle_error(loop, context):
        pass

    def start_loop():
        app = web.Application(loop=loop)
        app.router.add_resource("/").add_route("GET", handle_request)
        loop.run_until_complete(loop.create_server(app.make_handler(access_log=None), "0.0.0.0", 7340))
        try:
            loop.run_forever()
        except Exception:
            pass
        finally:
            loop.close()

    def stop_loop():
        def _stop(loop):
            loop.stop()

        loop.call_soon_threadsafe(_stop, loop)

    loop = asyncio.new_event_loop()
    loop.set_exception_handler(handle_error)
    t = threading.Thread(target=start_loop)
    t.start()
    wait_server_start("127.0.0.1:7340")
    request.addfinalizer(stop_loop)


class TestProxyAgentMiddleware:
    def test_handle_request(self, loop, monkeypatch):
        async def _pick_proxy():
            return "http://127.0.0.1"

        mw = ProxyAgentMiddleware.from_config(dict(proxy_agent_addr="http://127.0.0.1:7340"))
        monkeypatch.setattr(mw, "_pick_proxy", _pick_proxy)
        req = HttpRequest("http://www.example.com")
        loop.run_until_complete(mw.handle_request(req))
        assert req.proxy == "http://127.0.0.1"

    def test_pick_proxy(self, loop, monkeypatch):
        async def _update_proxy_list():
            if self.index < 2:
                self.index += 1
                mw._proxy_list = proxy_list[self.index - 1]

        self.index = 0
        proxy_list = [[], ["127.0.0.1", "127.0.0.2"]]
        res = ["http://127.0.0.1", "http://127.0.0.2"]
        mw = ProxyAgentMiddleware.from_config(dict(proxy_agent_addr="127.0.0.1:7340", proxy_update_interval=0.1))
        monkeypatch.setattr(mw, "_update_proxy_list", _update_proxy_list)
        for i in range(len(res)):
            req = HttpRequest("http://www.example.com")
            loop.run_until_complete(mw.handle_request(req))
            assert req.proxy in res

    def test_update_proxy_list(self, loop, monkeypatch, agent):
        async def _func():
            pass

        mw = ProxyAgentMiddleware.from_config(dict(proxy_agent_addr="http://127.0.0.1:7340", proxy_update_interval=0.1))
        mw._update_slot = 1
        monkeypatch.setattr(mw, "_update_slot_delay", _func)
        loop.run_until_complete(mw._update_proxy_list())
        assert mw._update_slot == 0 and mw._proxy_list == ["127.0.0.1:3128", "127.0.0.1:8080"]

    def test_update_slot_delay(self, loop):
        mw = ProxyAgentMiddleware.from_config(dict(proxy_agent_addr="http://127.0.0.1:7340", proxy_update_interval=0.1))
        mw._update_slot = 0
        t = time.time()
        loop.run_until_complete(mw._update_slot_delay())
        assert mw._update_slot == 1 and time.time() - t < 0.5


class TestRetryMiddleware:
    def test_handle_reponse(self, loop, monkeypatch):
        class ErrorFlag(Exception):
            pass

        def _retry(request, reason):
            assert isinstance(request, HttpRequest) and isinstance(reason, str)
            raise ErrorFlag

        mw = RetryMiddleware.from_config({})
        monkeypatch.setattr(mw, "retry", _retry)
        req = HttpRequest("http://www.example.com")
        resp = HttpResponse("http://www.example.com", 400)
        loop.run_until_complete(mw.handle_response(req, resp))
        with pytest.raises(ErrorFlag):
            resp = HttpResponse("http://www.example.com", 503)
            loop.run_until_complete(mw.handle_response(req, resp))

    def test_handle_error(self, loop, monkeypatch):
        class ErrorFlag(Exception):
            pass

        def _retry(request, reason):
            assert isinstance(request, HttpRequest) and isinstance(reason, str)
            raise ErrorFlag

        mw = RetryMiddleware.from_config({})
        monkeypatch.setattr(mw, "retry", _retry)
        req = HttpRequest("http://www.example.com")
        err = ValueError()
        loop.run_until_complete(mw.handle_error(req, err))
        with pytest.raises(ErrorFlag):
            err = ResponseNotMatch()
            loop.run_until_complete(mw.handle_error(req, err))

    def test_retry(self):
        max_retry_times = 2
        mw = RetryMiddleware.from_config(dict(max_retry_times=max_retry_times))
        req = HttpRequest("http://www.example.com")
        for i in range(max_retry_times):
            req = mw.retry(req, "")
            assert isinstance(req, HttpRequest)
        with pytest.raises(IgnoreRequest):
            req = mw.retry(req, "")
