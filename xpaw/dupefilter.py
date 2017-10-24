# coding=utf-8

import logging

from xpaw.utils.http import request_fingerprint

log = logging.getLogger(__name__)


class Dupefilter:
    def is_duplicated(self, request):
        raise NotImplementedError

    def open(self):
        pass

    def close(self):
        pass


class SetDupeFilter(Dupefilter):
    def __init__(self):
        self.hash = set()

    def is_duplicated(self, request):
        h = request_fingerprint(request)
        if h in self.hash:
            log.debug("Find the request (method={}, url={}) is duplicated".format(request.method, request.url))
            return True
        self.hash.add(h)
        return False
