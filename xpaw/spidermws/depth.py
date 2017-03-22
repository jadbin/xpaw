# coding=utf-8

import logging

from xpaw.http import HttpRequest

log = logging.getLogger(__name__)


class MaxDepthMiddleware:
    def __init__(self, max_depth):
        self._max_depth = max_depth

    @classmethod
    def from_config(cls, config):
        return cls(config.getint("max_depth", 0))

    def handle_output(self, response, result):
        depth = response.meta.get("_current_depth", 0) + 1
        for r in result:
            if isinstance(r, HttpRequest):
                if depth <= self._max_depth:
                    r.meta["_current_depth"] = depth
                    yield r
                else:
                    log.debug("The request(url={}) will be aborted as the depth of it is out of limit".format(r.url))
            else:
                yield r
