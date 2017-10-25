# coding=utf-8

import json
import random

from xpaw.http import HttpRequest
from xpaw.downloader import Downloader, DownloaderMiddlewareManager
from xpaw.downloadermws import CookieJarMiddleware


async def test_cookies(loop):
    downloader = Downloader(timeout=20, loop=loop)
    seed = str(random.randint(0, 2147483647))
    req = HttpRequest("http://httpbin.org/cookies", cookies={"seed": seed})
    resp = await downloader.download(req)
    cookies = json.loads(resp.text)["cookies"]
    assert len(cookies) == 1 and cookies.get("seed") == seed


async def test_cookie_jar(loop):
    downloader = Downloader(timeout=20, loop=loop)
    dmm = DownloaderMiddlewareManager(CookieJarMiddleware(loop=loop))
    seed = str(random.randint(0, 2147483647))
    await dmm.download(downloader, HttpRequest("http://httpbin.org/cookies/set?seed={}".format(seed)))
    resp = await dmm.download(downloader, HttpRequest("http://httpbin.org/cookies"))
    cookies = json.loads(resp.text)["cookies"]
    assert len(cookies) == 1 and cookies.get("seed") == seed
    await dmm.download(downloader, HttpRequest("http://httpbin.org/cookies/delete?seed="))
    resp = await dmm.download(downloader, HttpRequest("http://httpbin.org/cookies"))
    cookies = json.loads(resp.text)["cookies"]
    assert len(cookies) == 0
