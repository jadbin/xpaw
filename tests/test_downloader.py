# coding=utf-8

import json

import pytest

from xpaw.http import HttpRequest
from xpaw.downloader import Downloader
from xpaw.errors import HttpError
from xpaw.utils import make_url


@pytest.mark.asyncio
async def test_basic_auth():
    downloader = Downloader()

    async def no_auth():
        req = HttpRequest("http://httpbin.org/basic-auth/user/passwd")
        with pytest.raises(HttpError) as e:
            await downloader.fetch(req)
        assert e.value.response.status == 401

    async def tuple_auth():
        req = HttpRequest("http://httpbin.org/basic-auth/user/passwd")
        req.auth = ('user', 'passwd')
        resp = await downloader.fetch(req)
        assert resp.status == 200

    await no_auth()
    await tuple_auth()


@pytest.mark.asyncio
async def test_params():
    downloader = Downloader()

    async def query_params():
        url = "http://httpbin.org/anything?key=value&none="
        resp = await downloader.fetch(HttpRequest(url))
        assert json.loads(resp.text)['args'] == {'key': 'value', 'none': ''}

    async def dict_params():
        resp = await downloader.fetch(
            HttpRequest(make_url("http://httpbin.org/get", params={'key': 'value', 'none': ''})))
        assert json.loads(resp.text)['args'] == {'key': 'value', 'none': ''}

    async def list_params():
        resp = await downloader.fetch(HttpRequest(make_url("http://httpbin.org/get",
                                                           params=[('list', '1'), ('list', '2')])))
        assert json.loads(resp.text)['args'] == {'list': ['1', '2']}

    await query_params()
    await dict_params()
    await list_params()


@pytest.mark.asyncio
async def test_headers():
    downloader = Downloader()
    headers = {'User-Agent': 'xpaw'}
    resp = await downloader.fetch(HttpRequest("http://httpbin.org/get",
                                              headers=headers))
    assert resp.status == 200
    data = json.loads(resp.text)['headers']
    assert 'User-Agent' in data and data['User-Agent'] == 'xpaw'


@pytest.mark.asyncio
async def test_body():
    downloader = Downloader()

    async def post_str():
        str_data = 'str data: 字符串数据'
        resp = await downloader.fetch(HttpRequest('http://httpbin.org/post',
                                                  'POST', body=str_data,
                                                  headers={'Content-Type': 'text/plain'}))
        assert resp.status == 200
        body = json.loads(resp.text)['data']
        assert body == str_data

    async def post_bytes():
        bytes_data = 'bytes data: 字节数据'
        resp = await downloader.fetch(HttpRequest('http://httpbin.org/post',
                                                  'POST', body=bytes_data.encode(),
                                                  headers={'Content-Type': 'text/plain'}))
        assert resp.status == 200
        body = json.loads(resp.text)['data']
        assert body == bytes_data

    await post_str()
    await post_bytes()


@pytest.mark.asyncio
async def test_allow_redirects():
    downloader = Downloader()

    resp = await downloader.fetch(HttpRequest(make_url('http://httpbin.org/redirect-to',
                                                       params={'url': 'http://python.org'})))
    assert resp.status // 100 == 2 and 'python.org' in resp.url

    with pytest.raises(HttpError) as e:
        await downloader.fetch(HttpRequest(make_url('http://httpbin.org/redirect-to',
                                                    params={'url': 'http://python.org'}),
                                           allow_redirects=False))
    assert e.value.response.status // 100 == 3
