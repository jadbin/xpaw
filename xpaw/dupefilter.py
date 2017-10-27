# coding=utf-8

import logging

from xpaw.utils import request_fingerprint

log = logging.getLogger(__name__)


class DupeFilter:
    async def is_duplicated(self, request):
        raise NotImplementedError


class SetDupeFilter(DupeFilter):
    def __init__(self):
        self.hash = set()

    async def is_duplicated(self, request):
        if request.dont_filter:
            return False
        h = request_fingerprint(request)
        if h in self.hash:
            log.debug("Find the request (method={}, url={}) is duplicated".format(request.method, request.url))
            return True
        self.hash.add(h)
        return False
