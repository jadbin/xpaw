# coding=utf-8

import pytest
import json

import asyncio

from xpaw import HttpRequest
from xpaw.downloader import Downloader, DownloaderMiddlewareManager
from xpaw.downloadermws import CookieJarMiddleware


@pytest.fixture(scope="module")
def loop(request):
    def close():
        loop.close()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    request.addfinalizer(close)
    return loop


@pytest.fixture(scope="module")
def downloader(loop):
    return Downloader(timeout=20, loop=loop)


def test_cookies(downloader, loop):
    req = HttpRequest("http://httpbin.org/cookies", cookies={"k1": "v1", "k2": "v2"})
    resp = loop.run_until_complete(downloader.download(req))
    cookies = json.loads(resp.text)["cookies"]
    assert len(cookies) == 2 and cookies.get("k1") == "v1" and cookies.get("k2") == "v2"


def test_cookie_jar(downloader, loop):
    dmm = DownloaderMiddlewareManager(CookieJarMiddleware(loop=loop))
    loop.run_until_complete(dmm.download(downloader, HttpRequest("http://httpbin.org/cookies/set?k1=v1&k2=v2")))
    resp = loop.run_until_complete(dmm.download(downloader, HttpRequest("http://httpbin.org/cookies")))
    cookies = json.loads(resp.text)["cookies"]
    assert len(cookies) == 2 and cookies.get("k1") == "v1" and cookies.get("k2") == "v2"
    loop.run_until_complete(dmm.download(downloader, HttpRequest("http://httpbin.org/cookies/delete?k1=")))
    resp = loop.run_until_complete(dmm.download(downloader, HttpRequest("http://httpbin.org/cookies")))
    cookies = json.loads(resp.text)["cookies"]
    assert len(cookies) == 1 and cookies.get("k2") == "v2"
