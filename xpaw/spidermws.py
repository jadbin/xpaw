# coding=utf-8

import math
import logging

from .http import HttpRequest

log = logging.getLogger(__name__)


class DepthMiddleware:
    def __init__(self, max_depth=None):
        if max_depth is None or max_depth <= 0:
            self._max_depth = math.inf
        else:
            self._max_depth = max_depth

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config.getint("max_depth"))

    def handle_output(self, response, result):
        depth = response.meta.get("depth", 0) + 1
        for r in result:
            if isinstance(r, HttpRequest):
                r.meta["depth"] = depth
                if depth <= self._max_depth:
                    yield r
                else:
                    log.debug("The request(url=%s) will be aborted as the depth of it is out of limit", r.url)
            else:
                yield r
