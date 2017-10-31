# coding=utf-8

import json
import random
import asyncio

from aiohttp.helpers import BasicAuth
from aiohttp.client_reqrep import MultiDict

from xpaw.http import HttpRequest
from xpaw.downloader import Downloader


async def test_cookies(loop):
    downloader = Downloader(timeout=60, loop=loop)
    seed = str(random.randint(0, 2147483647))
    req = HttpRequest("http://httpbin.org/cookies", cookies={"seed": seed})
    resp = await downloader.download(req)
    cookies = json.loads(resp.text)["cookies"]
    assert len(cookies) == 1 and cookies.get("seed") == seed


async def test_cookie_jar(loop):
    downloader = Downloader(timeout=60, cookie_jar_enabled=True, loop=loop)
    seed = str(random.randint(0, 2147483647))
    await downloader.download(HttpRequest("http://httpbin.org/cookies/set?seed={}".format(seed)))
    resp = await downloader.download(HttpRequest("http://httpbin.org/cookies"))
    cookies = json.loads(resp.text)["cookies"]
    assert len(cookies) == 1 and cookies.get("seed") == seed
    await downloader.download(HttpRequest("http://httpbin.org/cookies/delete?seed="))
    resp = await downloader.download(HttpRequest("http://httpbin.org/cookies"))
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


