# coding=utf-8

import logging

from .http import HttpRequest

log = logging.getLogger(__name__)


class DepthMiddleware:
    def __init__(self, config):
        self._max_depth = config.getint("max_depth")

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(max_depth={})'.format(cls_name, repr(self._max_depth))

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config)

    def handle_output(self, response, result):
        depth = response.meta.get("depth", 0) + 1
        for r in result:
            if isinstance(r, HttpRequest):
                r.meta["depth"] = depth
                if self._max_depth is None or depth <= self._max_depth:
                    yield r
                else:
                    log.debug("The request %s will be aborted as the depth > %s", r, self._max_depth)
            else:
                yield r

    def handle_start_requests(self, result):
        for r in result:
            if isinstance(r, HttpRequest):
                r.meta['depth'] = 0
            yield r
