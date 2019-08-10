# coding=utf-8

import logging

from xpaw.errors import NotEnabled

log = logging.getLogger(__name__)

__all__ = ['DefaultHeadersMiddleware']


class DefaultHeadersMiddleware:
    def __init__(self, default_headers=None):
        self._headers = default_headers or {}

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(default_headers={})'.format(cls_name, repr(self._headers))

    @classmethod
    def from_crawler(cls, crawler):
        default_headers = crawler.config.get("default_headers")
        if default_headers is None:
            raise NotEnabled
        return cls(default_headers=default_headers)

    def handle_request(self, request):
        for k, v in self._headers.items():
            request.headers.setdefault(k, v)
