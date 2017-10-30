# coding=utf-8

from xpaw.config import Config
from xpaw.spidermws import *
from xpaw.http import HttpRequest


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

        mw = DepthMiddleware.from_cluster(Cluster(request_depth={'max_depth': 1}))
        req = HttpRequest("http://httpbin.org", "GET")
        res = [i for i in mw.handle_output(R(), [req])]
        assert res == [req] and req.meta['depth'] == 1
        res = [i for i in mw.handle_output(R(0), [req])]
        assert res == [req] and req.meta['depth'] == 1
        res = [i for i in mw.handle_output(R(1), [req])]
        assert res == [] and req.meta['depth'] == 2
