# coding=utf-8

import pytest

from xpaw.config import Config
from xpaw.spidermws import *
from xpaw.http import HttpRequest, HttpResponse
from xpaw.item import Item
from xpaw.errors import HttpError


class Cluster:
    def __init__(self, loop=None, **kwargs):
        self.loop = loop
        self.config = Config(kwargs)


class TestDepthMiddleware:
    def test_handle_output(self):
        class R:
            def __init__(self, depth=None):
                self.meta = {}
                if depth is not None:
                    self.meta["depth"] = depth

        mw = DepthMiddleware.from_cluster(Cluster(max_depth=1))
        req = HttpRequest("http://python.org/", "GET")
        item = Item()
        res = [i for i in mw.handle_output(R(), [req, item])]
        assert res == [req, item] and req.meta['depth'] == 1
        res = [i for i in mw.handle_output(R(0), [req, item])]
        assert res == [req, item] and req.meta['depth'] == 1
        res = [i for i in mw.handle_output(R(1), [req, item])]
        assert res == [item] and req.meta['depth'] == 2

    def test_handle_start_requests(self):
        mw = DepthMiddleware.from_cluster(Cluster())
        req = HttpRequest("http://python.org/", "GET")
        res = [i for i in mw.handle_start_requests([req])]
        for r in res:
            assert r.meta.get('depth') == 0


class TestHttpErrorMiddleware:
    def test_handle_input(self):
        mw = HttpErrorMiddleware()
        resp_200 = HttpResponse('', 200)
        resp_500 = HttpResponse('', 500)
        assert mw.handle_input(resp_200) is None
        with pytest.raises(HttpError):
            mw.handle_input(resp_500)

    def test_allow_all_http_status(self):
        mw = HttpErrorMiddleware.from_cluster(Cluster(allow_all_http_status=True))
        resp_200 = HttpResponse('', 200)
        assert mw.handle_input(resp_200) is None
        resp_500 = HttpResponse('', 500)
        assert mw.handle_input(resp_500) is None
