# coding=utf-8

import logging

from xpaw.errors import ResponseNotMatch, IgnoreRequest, NetworkError

log = logging.getLogger(__name__)


class RetryMiddleware:
    RETRY_ERRORS = (NetworkError, ResponseNotMatch)
    RETRY_HTTP_STATUS = (500, 502, 503, 504, 408)

    def __init__(self, max_retry_times):
        self._max_retry_times = max_retry_times

    @classmethod
    def from_config(cls, config):
        return cls(config.get("max_retry_times"))

    async def handle_response(self, request, response):
        if response.status in self.RETRY_HTTP_STATUS:
            return self.retry(request, "http status={}".format(response.status))

    async def handle_error(self, request, error):
        if isinstance(error, self.RETRY_ERRORS):
            return self.retry(request, "{}: {}".format(type(error), error))

    def retry(self, request, reason):
        retry_times = request.meta.get("_retry_times", 0) + 1
        if retry_times <= self._max_retry_times:
            log.debug("We will retry the request(url={}) because of {}".format(request.url, reason))
            request.meta["_retry_times"] = retry_times
            return request.copy()
        else:
            log.info("The request(url={}) has been retried {} times,"
                     " and it will be aborted.".format(request.url, self._max_retry_times))
            raise IgnoreRequest()
