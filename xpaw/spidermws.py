# coding=utf-8

import math
import logging

from .http import HttpRequest

log = logging.getLogger(__name__)


class DepthMiddleware:
    def __init__(self, config):
        self._max_depth = config.getint("max_depth", 0)
        if self._max_depth <= 0:
            self._max_depth = math.inf

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config)

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
