# coding=utf-8

import pytest

from xpaw.config import Config
from xpaw.spidermws import *
from xpaw.http import HttpRequest
from xpaw.item import Item
from xpaw.errors import NotEnabled


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
        req = HttpRequest("http://httpbin.org", "GET")
        item = Item()
        res = [i for i in mw.handle_output(R(), [req, item])]
        assert res == [req, item] and req.meta['depth'] == 1
        res = [i for i in mw.handle_output(R(0), [req, item])]
        assert res == [req, item] and req.meta['depth'] == 1
        res = [i for i in mw.handle_output(R(1), [req, item])]
        assert res == [item] and req.meta['depth'] == 2

    def test_handle_start_requests(self):
        mw = DepthMiddleware.from_cluster(Cluster())
        req = HttpRequest("http://httpbin.org", "GET")
        mw.handle_start_requests([req])
        assert req.meta.get('depth') == 0
