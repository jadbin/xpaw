# coding=utf-8

import logging

from xpaw.http import HttpRequest

log = logging.getLogger(__name__)

__all__ = ['DepthMiddleware']


class DepthMiddleware:
    def __init__(self, max_depth=None):
        self._max_depth = max_depth

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(max_depth={})'.format(cls_name, repr(self._max_depth))

    @classmethod
    def from_crawler(cls, crawler):
        config = crawler.config
        max_depth = config.getint('max_depth')
        return cls(max_depth=max_depth)

    def handle_spider_output(self, response, result):
        depth = response.meta.get('depth', 0) + 1
        for r in result:
            if isinstance(r, HttpRequest):
                r.meta['depth'] = depth
                if self._max_depth is None or depth <= self._max_depth:
                    yield r
                else:
                    log.debug("Abort %s: depth > %s", r, self._max_depth)
            else:
                yield r

    def handle_start_requests(self, result):
        for r in result:
            if isinstance(r, HttpRequest):
                r.meta['depth'] = 0
            yield r
