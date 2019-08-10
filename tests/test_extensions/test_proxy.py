# coding=utf-8


import pytest

from xpaw.http import HttpRequest
from xpaw.extensions import ProxyMiddleware
from xpaw.errors import NotEnabled

from ..crawler import Crawler


class Random:
    def __init__(self):
        self.iter = 0

    def choice(self, seq):
        res = seq[self.iter % len(seq)]
        self.iter += 1
        return res


class TestProxyMiddleware:
    def test_proxy_str(self):
        proxy = '127.0.0.1:3128'
        mw = ProxyMiddleware.from_crawler(Crawler(proxy=proxy))
        req = HttpRequest("http://example.com")
        mw.handle_request(req)
        assert req.proxy == proxy

    def test_proxy_dict(self):
        proxy_dict = {'http': '127.0.0.1:3128', 'https': '127.0.0.1:3129'}
        mw = ProxyMiddleware.from_crawler(Crawler(proxy=proxy_dict))
        req_list = []
        for i in ['http://example.com', 'https://example.com']:
            req_list.append(HttpRequest(i))
        res = ['127.0.0.1:3128', '127.0.0.1:3129']
        for i in range(len(req_list)):
            mw.handle_request(req_list[i])
            assert req_list[i].proxy == res[i]

    @pytest.mark.asyncio
    async def test_not_enabled(self):
        with pytest.raises(NotEnabled):
            ProxyMiddleware.from_crawler(Crawler())
