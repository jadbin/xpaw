# coding=utf-8

import random
import logging

log = logging.getLogger(__name__)


class ForwardForChinaMiddleware:
    async def handle_request(self, request):
        x = "61.%s.%s.%s" % (random.randint(128, 191), random.randint(0, 255), random.randint(1, 254))
        log.debug("Assign 'X-Forwarded-For: {0}' to request (url={1})".format(x, request.url))
        request.headers["X-Forwarded-For"] = x
