# coding=utf-8

import pytest

from xpaw.extensions import DefaultHeadersMiddleware
from xpaw.http import HttpRequest
from xpaw.errors import NotEnabled

from ..crawler import Crawler


class TestDefaultHeadersMiddleware:
    def test_handle_request(self):
        default_headers = {"User-Agent": "xpaw", "Connection": "keep-alive"}
        mw = DefaultHeadersMiddleware.from_crawler(Crawler(default_headers=default_headers))
        req = HttpRequest("http://example.com", headers={"Connection": "close"})
        mw.handle_request(req)
        assert req.headers == {"User-Agent": "xpaw", "Connection": "close"}

    def test_not_enabled(self):
        with pytest.raises(NotEnabled):
            DefaultHeadersMiddleware.from_crawler(Crawler(default_headers=None))
