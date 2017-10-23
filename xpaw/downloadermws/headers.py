# coding=utf-8

import logging
import random

log = logging.getLogger(__name__)


class RequestHeadersMiddleware:
    def __init__(self, headers):
        self._headers = headers or {}

    @classmethod
    def from_config(cls, config):
        return cls(config.get("request_headers"))

    async def handle_request(self, request):
        log.debug("Assign headers to request (url={}): {}".format(request.url, self._headers))
        for i in self._headers:
            request.headers[i] = self._headers[i]


class ForwardedForMiddleware:
    async def handle_request(self, request):
        x = "61.%s.%s.%s" % (random.randint(128, 191), random.randint(0, 255), random.randint(1, 254))
        log.debug("Assign 'X-Forwarded-For: {}' to request (url={})".format(x, request.url))
        request.headers["X-Forwarded-For"] = x
