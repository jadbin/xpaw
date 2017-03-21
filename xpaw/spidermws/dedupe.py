# coding=utf-8

import logging

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


class LocalSetDedupeMiddleware(DedupeMiddleware):
    def __init__(self):
        self._url_set = set()

    def _is_dupe(self, request):
        s = request.method + " " + request.url
        if s not in self._url_set:
            self._url_set.add(s)
            return False
        return True
