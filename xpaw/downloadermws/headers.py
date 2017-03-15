# coding=utf-8

import logging

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
