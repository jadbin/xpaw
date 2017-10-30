# coding=utf-8

import logging

from xpaw.http import HttpRequest

log = logging.getLogger(__name__)


class DepthMiddleware:
    def __init__(self, max_depth):
        self._max_depth = max_depth

    @classmethod
    def from_cluster(cls, cluster):
        c = cluster.config.get("request_depth")
        return cls(**c)

    def handle_output(self, response, result):
        depth = response.meta.get("depth", 0) + 1
        for r in result:
            if isinstance(r, HttpRequest):
                r.meta["depth"] = depth
                if depth <= self._max_depth:
                    yield r
                else:
                    log.debug("The request(url={}) will be aborted as the depth of it is out of limit".format(r.url))
            else:
                yield r
