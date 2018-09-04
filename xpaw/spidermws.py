# coding=utf-8

import logging

from .http import HttpRequest
from .errors import HttpError

log = logging.getLogger(__name__)


class DepthMiddleware:
    def __init__(self, max_depth):
        self._max_depth = max_depth

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(max_depth={})'.format(cls_name, repr(self._max_depth))

    @classmethod
    def from_cluster(cls, cluster):
        config = cluster.config
        max_depth = config.getint("max_depth")
        return cls(max_depth=max_depth)

    def handle_output(self, response, result):
        depth = response.meta.get("depth", 0) + 1
        for r in result:
            if isinstance(r, HttpRequest):
                r.meta["depth"] = depth
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


class HttpErrorMiddleware:
    def __init__(self, allow_all_http_status=False):
        self._allow_all_http_status = allow_all_http_status

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(allow_all_http_status={})'.format(cls_name, self._allow_all_http_status)

    @classmethod
    def from_cluster(cls, cluster):
        config = cluster.config
        allow_all_http_status = config.getbool("allow_all_http_status")
        return cls(allow_all_http_status=allow_all_http_status)

    def handle_input(self, response):
        if 200 <= response.status < 300:
            return None
        if self._allow_all_http_status:
            return None
        raise HttpError('Ignore non-2xx response', response=response)
