# coding=utf-8

from xpaw.config import Config
from xpaw.spidermws import *
from xpaw.http import HttpRequest, HttpResponse


class TestDepthMiddleware:
    max_depth = 1
    key = "_current_depth"

    def test_handle_output(self):
        class R:
            def __init__(self, depth=None):
                self.meta = {}
                if depth is not None:
                    self.meta["_current_depth"] = depth

        mw = MaxDepthMiddleware.from_config(Config({"max_depth": 1}))
        req = HttpRequest("http://127.0.0.1", "GET")
        resp = HttpResponse("http://127.0.0.1", 200)
        res = [i for i in mw.handle_output(R(), [req, resp])]
        assert res == [req, resp] and req.meta[self.key] == 1
        res = [i for i in mw.handle_output(R(0), [req, resp])]
        assert res == [req, resp] and req.meta[self.key] == 1
        res = [i for i in mw.handle_output(R(1), [req, resp])]
        assert res == [resp]
