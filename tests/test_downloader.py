# coding=utf-8

import json
import random
import asyncio

from aiohttp.helpers import BasicAuth

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


async def test_basic_auth(loop):
    downloader = Downloader(timeout=20, loop=loop)

    def validate_response(resp, login):
        assert resp.status == 200
        data = json.loads(resp.body.decode())
        assert data['authenticated'] is True and data['user'] == login

    async def no_auth():
        resp = await downloader.download(HttpRequest("http://httpbin.org/basic-auth/login/password"))
        assert resp.status == 401

    async def str_auth():
        resp = await downloader.download(HttpRequest("http://httpbin.org/basic-auth/login/password",
                                                     auth='login@password'))
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
