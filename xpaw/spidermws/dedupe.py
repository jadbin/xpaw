# coding=utf-8

import logging

from pymongo import MongoClient

from xpaw.http import HttpRequest

log = logging.getLogger(__name__)


class DedupeMiddleware:
    def handle_output(self, response, result):
        return self._handle_result(result)

    def handle_start_requests(self, result):
        return self._handle_result(result)

    def _handle_result(self, result):
        for r in result:
            if isinstance(r, HttpRequest):
                if not self._is_dupe(r):
                    yield r
                else:
                    log.debug("Find the request (method={}, url={}) is duplicated".format(r.method, r.url))
            else:
                yield r

    def _is_dupe(self, request):
        raise NotImplementedError


class MongoDedupeMiddleware(DedupeMiddleware):
    def __init__(self, mongo_addr, mongo_db, mongo_tbl):
        mongo_client = MongoClient(mongo_addr)
        self._dedupe_tbl = mongo_client[mongo_db][mongo_tbl]
        self._dedupe_tbl.create_index("request")

    @classmethod
    def from_config(cls, config):
        task_id = config.get("task_id")
        return cls(config.get("mongo_dedupe"),
                   "xpaw_dedupe",
                   "task_{}".format(task_id))

    def _is_dupe(self, request):
        res = self._dedupe_tbl.find_one({"request": request.method + " " + request.url})
        if res is None:
            self._dedupe_tbl.insert_one({"request": request.method + " " + request.url})
            return False
        return True


class LocalSetDedupeMiddleware(DedupeMiddleware):
    def __init__(self):
        self._url_set = set()

    def _is_dupe(self, request):
        s = request.method + " " + request.url
        if s not in self._url_set:
            self._url_set.add(s)
            return False
        return True
