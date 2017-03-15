# coding=utf-8

import pytest

from xpaw.spidermws import *
from xpaw.http import HttpRequest, HttpResponse


class MongoClientMock:
    def __init__(self, mongo_addr):
        self.mongo_addr = mongo_addr

    def __getitem__(self, name):
        return MongoDatabaseMock(self, name)


class MongoDatabaseMock:
    def __init__(self, client, name):
        self.client = client
        self.name = name

    def __getitem__(self, name):
        return MongoCollectionMock(self, name)


class MongoCollectionMock:
    def __init__(self, database, name):
        self.database = database
        self.name = name
        self.index = None
        self.data = set()

    def create_index(self, name):
        self.index = name

    def find_one(self, req):
        assert len(req) == 1
        key, value = None, None
        for i, j in req.items():
            key, value = i, j
        assert key == self.index
        if value in self.data:
            return value

    def insert_one(self, req):
        assert len(req) == 1
        key, value = None, None
        for i, j in req.items():
            key, value = i, j
        assert key == self.index
        self.data.add(value)


@pytest.fixture(scope="function")
def mongo_client_patch(request, monkeypatch):
    monkeypatch.setattr(dedupe, "MongoClient", MongoClientMock)
    request.addfinalizer(lambda: monkeypatch.undo())


class TestMongoDedupeMiddleware:
    task_id = "0123456789abcdef"
    mongo_dedupe = "mongodb://root:123456@127.0.0.1:27017"
    mongo_dedupe_db = "xpaw_dedupe"
    mongo_dedupe_tbl = "task_{}".format(task_id)
    req1 = HttpRequest("http://127.0.0.1", "GET")
    req2 = HttpRequest("http://127.0.0.2", "GET")
    req3 = HttpRequest("http://127.0.0.1", "POST")
    resp = HttpResponse("http://127.0.0.1", 200)
    req_list = [req1,
                HttpRequest("http://127.0.0.1", "GET"),
                req2,
                req3,
                resp,
                HttpRequest("http://127.0.0.1", "POST")]
    res_list = [req1, req2, req3, resp]

    def test_handle_start_requests(self, mongo_client_patch):
        mw = MongoDedupeMiddleware.from_config(dict(task_id=self.task_id, mongo_dedupe=self.mongo_dedupe))
        assert mw._dedupe_tbl.name == self.mongo_dedupe_tbl
        assert mw._dedupe_tbl.database.name == self.mongo_dedupe_db
        assert mw._dedupe_tbl.database.client.mongo_addr == self.mongo_dedupe
        res = [i for i in mw.handle_start_requests(self.req_list)]
        assert res == self.res_list

    def test_handle_output(self, mongo_client_patch):
        mw = MongoDedupeMiddleware.from_config(dict(task_id=self.task_id, mongo_dedupe=self.mongo_dedupe))
        assert mw._dedupe_tbl.name == self.mongo_dedupe_tbl
        assert mw._dedupe_tbl.database.name == self.mongo_dedupe_db
        assert mw._dedupe_tbl.database.client.mongo_addr == self.mongo_dedupe
        res = [i for i in mw.handle_output(None, self.req_list)]
        assert res == self.res_list


class TestDepthMiddleware:
    max_depth = 1
    key = "_current_depth"

    def test_handle_output(self):
        class R:
            def __init__(self, depth=None):
                self.meta = {}
                if depth is not None:
                    self.meta["_current_depth"] = depth

        mw = DepthMiddleware.from_config(dict(max_depth=1))
        req = HttpRequest("http://127.0.0.1", "GET")
        resp = HttpResponse("http://127.0.0.1", 200)
        res = [i for i in mw.handle_output(R(), [req, resp])]
        assert res == [req, resp] and req.meta[self.key] == 1
        res = [i for i in mw.handle_output(R(0), [req, resp])]
        assert res == [req, resp] and req.meta[self.key] == 1
        res = [i for i in mw.handle_output(R(1), [req, resp])]
        assert res == [resp]
