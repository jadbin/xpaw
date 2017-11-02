# coding=utf-8

import logging

from .utils import request_fingerprint

log = logging.getLogger(__name__)


class SetDupeFilter:
    def __init__(self):
        self._hash = set()

    async def is_duplicated(self, request):
        if request.dont_filter:
            return False
        h = request_fingerprint(request)
        if h in self._hash:
            log.debug("Find the request (method=%s, url=%s) is duplicated", request.method, request.url)
            return True
        self._hash.add(h)
        return False

    def clear(self):
        self._hash.clear()
